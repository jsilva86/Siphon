import re

from typing import List, Dict

from slither.core.cfg.node import NodeType, Node
from slither.core.solidity_types.type import Type
from slither.core.solidity_types.array_type import ArrayType
from slither.core.solidity_types.mapping_type import MappingType

from modules.cfg_builder.cfg import CFG, Block, cfg_to_dot

from modules.pattern_matcher.patternMatcher import (
    Pattern,
    PatternType,
    RedundantCodePattern,
    OpaquePredicatePattern,
    ExpensiveOperationInLoopPattern,
    LoopInvariantOperationPattern,
    LoopInvariantConditionPattern,
)

from modules.code_optimizer.codeGenerator import get_source_line_from_node
from modules.code_optimizer.siphonNode import SiphonNode


class Optimizer:
    """
    OptimizerSingleton class

    """

    instance = None

    _function_name: str = ""

    _cfg: CFG = None

    _optimized_cfg: Block = None

    _patterns: List["Pattern"] = []

    _export_cfg: bool = False

    # generated placeholders and their scope
    _placeholder_variables: Dict[str, int] = {}

    # prefix for placeholder variables
    _placeholder_prefix: str = "SP_VAR_"

    # prefix for placeholder variables
    _type_prefix: str = "SP_TYPE_"

    @property
    def function_name(self) -> str:
        return self._function_name

    @property
    def cfg(self) -> CFG:
        return self._cfg

    @property
    def optimized_cfg(self) -> CFG:
        return self._optimized_cfg

    @property
    def patterns(self) -> List["Pattern"]:
        return self._patterns

    @property
    def export_cfg(self) -> bool:
        return self._export_cfg

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def placeholder_prefix(self) -> str:
        return self._placeholder_prefix

    @property
    def type_prefix(self) -> str:
        return self._type_prefix

    @staticmethod
    def get_instance():
        if not Optimizer.instance:
            Optimizer.instance = Optimizer()
        return Optimizer.instance

    def init_instance(
        self, function_name, cfg: CFG, patterns: List["Pattern"], export_cfg=False
    ):
        self._function_name = function_name

        self._cfg = cfg

        self._patterns = patterns

        # debug optimized CFG
        self._export_cfg = export_cfg

    def generate_optimized_cfg(self):
        for pattern in self.patterns:
            match pattern.pattern_type:
                case PatternType.REDUNDANT_CODE:
                    self.handle_redundant_code(pattern)
                case PatternType.OPAQUE_PREDICATE:
                    self.handle_opaque_predicate(pattern)
                case PatternType.EXPENSIVE_OPERATION_IN_LOOP:
                    self.handle_expensive_operation_in_loop(pattern)
                case PatternType.LOOP_INVARIANT_OPERATION:
                    self.handle_loop_invariant_operation(pattern)
                case PatternType.LOOP_INVARIANT_CONDITION:
                    self.handle_loop_invariant_condition(pattern)

        if self.export_cfg:
            cfg_to_dot(f"{self.function_name}-optimized", self.cfg.head)

        # return the optimized CFG
        return None

    def handle_redundant_code(self, pattern: RedundantCodePattern):
        # last instruction is the IF condition
        pattern.block._instructions.pop()

        # the false path is now the true path, IF it exists
        if pattern.block.false_path:
            pattern.block.true_path = pattern.block.false_path
            pattern.block.false_path = None
        else:
            pattern.block.true_path = None

    def handle_opaque_predicate(self, pattern: OpaquePredicatePattern):
        # last instruction is the IF condition
        # no need to have since it's always true
        pattern.block._instructions.pop()

        # since it's a tautology the nagation will never be executed
        # remove the branch if it exists
        if pattern.block.false_path:
            pattern.block.false_path = None

    def handle_expensive_operation_in_loop(
        self, pattern: ExpensiveOperationInLoopPattern
    ):
        # get the block scope where the access is being made
        block_of_scope = self.get_block_of_scope(pattern)

        # line that will be modified to reference the new Placeholder variable
        modified_source_line = get_source_line_from_node(pattern.instruction).decode()

        # find start of loop
        loop_start_index = self.find_begin_loop_index(block_of_scope.instructions)

        for variable_name, s_variable_name in zip(
            pattern.variables, pattern.sanitized_variables
        ):
            # search for the Storage variable via its sanitized name (structs/lists)
            variable_type = self._cfg.contract.variables_as_dict.get(
                s_variable_name
            ).type

            # generate unique name for placeholder
            placeholder_variable_name = self.generate_placeholder_name(
                variable_type, variable_name, s_variable_name
            )

            if self.should_generate_instructions(
                placeholder_variable_name, block_of_scope
            ):
                # store placeholder variable and its scope
                self._placeholder_variables[
                    placeholder_variable_name
                ] = block_of_scope.id

                # extract the value of Storage to Memory
                assignment = self.generate_storage_access(
                    variable_type,
                    variable_name,
                    s_variable_name,
                    placeholder_variable_name,
                )

                # GENERATE Assignment instruction
                assignment_instruction = SiphonNode(pattern.instruction, assignment)

                insert_index = loop_start_index - 1

                # in case the BEGIN_LOOP is the first instruction
                insert_index = max(insert_index, 0)

                # insert assignment before BEGIN_LOOP in block
                block_of_scope._instructions.insert(
                    insert_index, assignment_instruction
                )

                # write-back the value to Storage after loop
                # FIXME: write-back is not always need, array.length = placeholder is incorrect
                write_back = self.generate_write_back(
                    variable_type, variable_name, placeholder_variable_name
                )

                # GENERATE Write-Back instruction
                write_back_instruction = SiphonNode(pattern.instruction, write_back)

                # insert write-back after loop in block (false path)
                block_of_scope._false_path._instructions = [
                    write_back_instruction
                ] + block_of_scope._false_path._instructions

            # REPLACE storage access in line
            # same line can have multiple storage accesses
            modified_source_line = self.modify_source_line(
                variable_type,
                modified_source_line,
                variable_name,
                placeholder_variable_name,
            )

        # print(block_of_scope.false_path.id, block_of_scope.false_path._instructions)
        # print("original line", get_source_line_from_node(pattern.instruction))
        # print("modified line", modified_source_line)

        # GENERATE modified instruction
        modified_instruction = SiphonNode(pattern.instruction, modified_source_line)

        instruction_index = self.find_instruction_index(
            pattern.instruction, pattern.block.instructions
        )

        # replace instruction in block
        pattern.block._instructions[instruction_index] = modified_instruction

    def handle_loop_invariant_operation(self, pattern: LoopInvariantOperationPattern):
        pass

    def handle_loop_invariant_condition(self, pattern: LoopInvariantConditionPattern):
        pass

    def get_block_of_scope(self, pattern: ExpensiveOperationInLoopPattern) -> Block:
        """
        Given a block scope, stored in the pattern,
        traverse upwards in the CFG until the corresponding Block is found and return it
        """

        # when the current block has the id of the current scope return it
        current_block = pattern.block
        while current_block.id != pattern.current_scope:
            current_block = current_block.prev_block

        return current_block

    def generate_placeholder_name(
        self, variable_type: Type, variable_name: str, sanitized_variable_name: str
    ):
        """
        Generate a dummy variable to extract the value and then write back

        Deals with name collision in the contract and function
        """
        storage_variables = [str(variable) for variable in self._cfg.contract.variables]
        function_variables = [
            str(variable) for variable in self._cfg.function.variables
        ]

        prefix = self.placeholder_prefix
        suffix = 0
        new_variable_name = prefix + sanitized_variable_name

        # avoid name collision
        while (
            new_variable_name in storage_variables
            or new_variable_name in function_variables
        ):
            suffix += 1
            new_variable_name = prefix + sanitized_variable_name + "_" + str(suffix)

        if self.is_primitive_type(variable_type):
            return new_variable_name

        # if variable is not primitive account for indexable part to get unique name
        indexable_part = self.get_indexable_part(variable_name)

        # array/ array.<method>
        if not indexable_part:
            return new_variable_name

        new_variable_name += f"_{indexable_part}"

        return new_variable_name

    def should_generate_instructions(self, variable_name: str, start_block: Block):
        """
        Ensure that placeholders and write-backs are only generated once.

        Additionally, if a placeholder for the given variable_name
        was already generated in an higher scope don't generate it again
        and avoid writting it back as well
        """
        if variable_name not in self._placeholder_variables:
            return True

        placeholder_scope = self._placeholder_variables.get(variable_name)

        # starting on 'start_block', check if 'placeholder_block' is reachable
        # if it is, then a placeholder was already generate in an higher scope
        current_block = start_block
        while current_block:
            if current_block.id == placeholder_scope:
                return False

            if not current_block.prev_block:
                break

            current_block = current_block.prev_block

        # if block is not found then placeholder was never generated
        return True

    def generate_storage_access(
        self,
        variable_type: Type,
        original_var_name: str,
        sanitized_var_name: str,
        placeholder_var_name: str,
    ) -> str:
        if self.is_primitive_type(variable_type):
            return self.generate_primitive_access(
                variable_type, original_var_name, placeholder_var_name
            )

        elif self.is_array_type(variable_type):
            return self.generate_array_access(
                variable_type,
                original_var_name,
                sanitized_var_name,
                placeholder_var_name,
            )

        elif self.is_mapping_type(variable_type):
            return self.generate_mapping_access(
                variable_type,
                original_var_name,
                sanitized_var_name,
                placeholder_var_name,
            )

    def generate_primitive_access(
        self, variable_type: Type, original_var_name: str, placeholder_var_name: str
    ):
        # <var_type> placeholder_var_name = original_var_name
        return f"{str(variable_type)} {placeholder_var_name} = {original_var_name};"

    def generate_array_access(
        self,
        variable_type: Type,
        original_var_name: str,
        sanitized_var_name: str,
        placeholder_var_name: str,
    ):
        indexable_part = self.get_indexable_part(original_var_name)

        # direct assignment to array / array.<method>
        if not indexable_part:
            # <var_type>[] placeholder_var_name = sanitized_variable_name
            return (
                f"{str(variable_type)} {placeholder_var_name} = {sanitized_var_name};"
            )

        array_type = self.get_array_type(variable_type)

        # <array_el_type> placeholder_var_name = sanitized_variable_name
        return f"{array_type} {placeholder_var_name} = {original_var_name};"

    def generate_mapping_access(
        self,
        variable_type: Type,
        original_var_name: str,
        sanitized_var_name: str,
        placeholder_var_name: str,
    ):
        indexable_part = self.get_indexable_part(original_var_name)

        key_type, value_type = self.retrieve_mapping_types(variable_type)

        if not key_type or not value_type:
            return

        struct_name = self.generate_struct_name(sanitized_var_name)

        # key = indexable_part
        # value = original_var_name
        # SP_TYPE_<sanitized_var_name> memory placeholder_var_name = SP_TYPE_<sanitized_var_name>(key, value)
        return f"{struct_name} memory {placeholder_var_name} = {struct_name}({indexable_part}, {original_var_name});"

    def generate_write_back(
        self, variable_type: Type, original_var_name: str, placeholder_var_name: str
    ):
        if self.is_mapping_type(variable_type):
            # original_var_name = placeholder_var_name.value
            return f"{original_var_name} = {placeholder_var_name}.value;"

        # original_var_name = placeholder_var_name
        return f"{original_var_name} = {placeholder_var_name};"

    def modify_source_line(
        self,
        variable_type: Type,
        source_line: str,
        variable_name: str,
        placeholder_variable_name: str,
    ):
        if self.is_mapping_type(variable_type):
            # access value field in struct
            return source_line.replace(
                variable_name, f"{placeholder_variable_name}.value"
            )

        return source_line.replace(variable_name, placeholder_variable_name)

    def find_begin_loop_index(self, instructions: List["Node"]):
        try:
            return next(
                index
                for index, instruction in enumerate(instructions)
                if instruction.type == NodeType.STARTLOOP
            )
        except StopIteration:
            return -1

    def find_instruction_index(self, instruction: Node, instructions: List["Node"]):
        try:
            return next(
                index
                for index, inst in enumerate(instructions)
                if inst.node_id == instruction.node_id
            )
        except StopIteration:
            return -1

    def is_primitive_type(self, type: Type):
        return not isinstance(type, MappingType) and not isinstance(type, ArrayType)

    def is_mapping_type(self, type: Type):
        return isinstance(type, MappingType)

    def is_array_type(self, type: Type):
        return isinstance(type, ArrayType)

    def get_indexable_part(self, variable_name: str):
        """
        Variable must be mapping or array
        """
        return result[1] if (result := re.search(r"\[(.*?)\]", variable_name)) else None

    def get_array_type(self, variable_type: Type):
        return str(variable_type).split("[]")[0]

    def convert_mapping_to_struct(
        self, mapping_type: Type, variable_name: str, mapping_name: str
    ):
        key_type, value_type = self.retrieve_mapping_types(mapping_type)

        if not key_type or not value_type:
            return

        print(variable_name, mapping_name)
        print(key_type, value_type)

        struct_name = self.generate_struct_name(mapping_name)

        # TODO: generate mapping and return it

        print(struct_name)

    def retrieve_mapping_types(self, mapping_type: Type):
        pattern = r"mapping\((.*?)\s*=>\s*(.*?)\)"

        if not (match := re.search(pattern, str(mapping_type))):
            return None, None

        return match[1], match[2]

    def generate_struct_name(self, mapping_name: str):
        user_defined_types = [str(type) for type in self.cfg.contract.structures]

        prefix = self.type_prefix
        struct_name = prefix + mapping_name

        # avoid name collision with other types
        while struct_name in user_defined_types:
            suffix += 1
            struct_name = prefix + struct_name + "_" + str(suffix)

        return struct_name


# export the singleton
optimizerSingleton = Optimizer.get_instance()
