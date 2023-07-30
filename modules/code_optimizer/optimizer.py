import re
import hashlib

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

    _cfg: CFG = None

    _patterns: List["Pattern"] = []

    _export_cfg: bool = False

    # generated placeholders and their scope
    _placeholder_variables: Dict[str, int] = {}

    # prefix for placeholder variables
    _placeholder_prefix: str = "SP_"

    @property
    def cfg(self) -> CFG:
        return self._cfg

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

    @staticmethod
    def get_instance():
        if not Optimizer.instance:
            Optimizer.instance = Optimizer()
        return Optimizer.instance

    def init_instance(self, export_cfg=False):
        # debug optimized CFG
        self._export_cfg = export_cfg

    def update_instance(self, cfg: CFG, patterns: List["Pattern"]):
        # CFG to analyse
        self._cfg = cfg

        # Patterns to optimize
        self._patterns = patterns

    def generate_optimized_cfg(self):
        """
        Optimizes the current CFG
        """
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
            cfg_to_dot(f"{self.cfg.function.name}-optimized", self.cfg.head)

        # return the optimized cfg
        return self.cfg

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
                self.push_assignment_to_block(pattern, block_of_scope, assignment)

                # write-back the value to Storage after loop
                if self.should_generate_write_back(variable_type, variable_name):
                    write_back = self.generate_write_back(
                        variable_name, placeholder_variable_name
                    )

                    # GENERATE Write-Back instruction
                    self.push_write_back_to_block(pattern, block_of_scope, write_back)

            # REPLACE storage access in line
            # same line can have multiple storage accesses
            modified_source_line = self.modify_source_line(
                modified_source_line,
                variable_name,
                placeholder_variable_name,
            )

        # GENERATE modified instruction
        self.push_modified_line_to_block(pattern, modified_source_line)

    def handle_loop_invariant_operation(self, pattern: LoopInvariantOperationPattern):
        block_of_scope = self.get_block_of_scope(pattern)

        # line that will be modified to reference the new Placeholder variable
        modified_source_line = get_source_line_from_node(pattern.instruction).decode()

        for function, func_call in zip(pattern.functions, pattern.func_calls):
            func_name = str(function)

            # assume only one return type
            return_type = function.return_type[0]

            # generate unique name for placeholder
            placeholder_variable_name = self.generate_unique_name(func_name)

            # add func_arg info toa void name collision
            placeholder_variable_name = self.enhance_with_func_args(
                placeholder_variable_name, func_call
            )

            if self.should_generate_instructions(func_name, block_of_scope):
                # store placeholder variable and its scope
                self._placeholder_variables[
                    placeholder_variable_name
                ] = block_of_scope.id

                assignment = self.generate_func_call(
                    return_type, func_call, placeholder_variable_name
                )

                self.push_assignment_to_block(pattern, block_of_scope, assignment)

            # REPLACE func call in line
            # same line can have multiple func calls
            modified_source_line = self.modify_source_line(
                modified_source_line,
                func_call,
                placeholder_variable_name,
            )

        # GENERATE modified instruction
        self.push_modified_line_to_block(pattern, modified_source_line)

    def handle_loop_invariant_condition(self, pattern: LoopInvariantConditionPattern):
        block_of_scope = self.get_block_of_scope(pattern)

        if_condition = self.sanitize_if_condition(str(pattern.instruction))

        placeholder_var_name = self.hash_if_condition(if_condition)

        # line that will be modified to reference the new Placeholder variable
        modified_source_line = (
            get_source_line_from_node(pattern.instruction).decode().replace(" ", "")
        )

        if self.should_generate_instructions(placeholder_var_name, block_of_scope):
            # store placeholder variable and its scope
            self._placeholder_variables[placeholder_var_name] = block_of_scope.id

            assignment = self.generate_inline_if(if_condition, placeholder_var_name)

            self.push_assignment_to_block(pattern, block_of_scope, assignment)

        modified_source_line = self.safe_replace_if(
            modified_source_line,
            placeholder_var_name,
        )

        # GENERATE modified instruction
        self.push_modified_line_to_block(pattern, modified_source_line)

    def get_block_of_scope(self, pattern: Pattern) -> Block:
        """
        Given a block scope, stored in the pattern,
        traverse upwards in the CFG until the corresponding Block is found and return it
        """

        # when the current block has the id of the current scope return it
        current_block = pattern.block
        while current_block.id != pattern.current_scope:
            current_block = current_block.prev_block

        return current_block

    def generate_unique_name(self, name: str):
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
        new_variable_name = prefix + name

        # avoid name collision
        while (
            new_variable_name in storage_variables
            or new_variable_name in function_variables
        ):
            suffix += 1
            new_variable_name = prefix + name + "_" + str(suffix)

        return new_variable_name

    def hash_if_condition(self, condition: str):
        # Generate a unique hash for the condition using MD5
        hash_value = hashlib.md5(condition.encode()).hexdigest()

        return f"{self.placeholder_prefix}cond_{hash_value[:8]}"

    def generate_placeholder_name(
        self, variable_type: Type, variable_name: str, sanitized_variable_name: str
    ):
        # avoid name collision
        new_variable_name = self.generate_unique_name(sanitized_variable_name)

        if self.is_primitive_type(variable_type):
            return new_variable_name

        # if variable is not primitive account for indexable part to get unique name
        indexable_part = self.get_indexable_part(variable_name)

        # array/ array.<method>
        if not indexable_part:
            if self.is_method_over_array(variable_name):
                return f"{new_variable_name}_length"

            # FIXME: safeguard for direct assignments to arrays
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

    def should_generate_write_back(self, variable_type: Type, variable_name: str):
        # TODO: hardcoded to work for array.<method>
        # ideally would only write-back when needed
        if self.is_primitive_type(variable_type) or self.is_mapping_type(variable_type):
            return True

        indexable_part = self.get_indexable_part(variable_name)

        # array/ array.<method>
        return bool(indexable_part)

    def push_assignment_to_block(
        self,
        pattern: Pattern,
        block_of_scope: Block,
        assignment: str,
    ):
        """
        GENERATE Assignment instruction
        """
        assignment_instruction = SiphonNode(pattern.instruction, assignment)

        # find start of loop
        loop_start_index = self.find_begin_loop_index(block_of_scope.instructions)

        insert_index = loop_start_index - 1

        # in case the BEGIN_LOOP is the first instruction
        insert_index = max(insert_index, 0)

        # insert assignment before BEGIN_LOOP in block
        block_of_scope._instructions.insert(insert_index, assignment_instruction)

    def push_write_back_to_block(
        self, pattern: Pattern, block_of_scope: Block, write_back: str
    ):
        """
        GENERATE Write-Back instruction
        """
        write_back_instruction = SiphonNode(pattern.instruction, write_back)

        # insert write-back after loop in block (false path)
        block_of_scope._false_path._instructions = [
            write_back_instruction
        ] + block_of_scope._false_path._instructions

    def push_modified_line_to_block(self, pattern: Pattern, modified_source_line: str):
        """
        GENERATE modified instruction
        """
        modified_instruction = SiphonNode(pattern.instruction, modified_source_line)

        instruction_index = self.find_instruction_index(
            pattern.instruction, pattern.block.instructions
        )

        # replace instruction in block
        pattern.block._instructions[instruction_index] = modified_instruction

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
            if self.is_method_over_array(original_var_name):
                # uint256 placeholder_var_name = original_var_name
                return f"uint256 {placeholder_var_name} = {original_var_name};"

            # safeguard for direct assignments to arrays
            # TODO maybe filter this out in patternMatcher
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
        placeholder_var_name: str,
    ):
        _, value_type = self.retrieve_mapping_types(variable_type)

        if not value_type:
            return

        # <value_type> placeholder_var_name = original_var_name
        return f"{value_type} {placeholder_var_name} = {original_var_name};"

    def generate_write_back(self, original_var_name: str, placeholder_var_name: str):
        # original_var_name = placeholder_var_name
        return f"{original_var_name} = {placeholder_var_name};"

    def enhance_with_func_args(self, variable_name: str, func_call: str):
        """
        Add func_arg info to variable name to improve name collision
        """
        if func_args := self.get_func_call_args(func_call):
            abbreviated_args = [arg[:3] for arg in func_args]
            return f"{variable_name}_{'_'.join(abbreviated_args)}"
        return variable_name

    def get_func_call_args(self, func_call: str):
        # FIXME: duplicated in patternMatcher
        pattern = r"(\w+)\((.*)\)"
        # remove whitespaces
        func_call = re.sub(r"\s+", "", func_call)
        if match := re.match(pattern, func_call):
            return match[2].split(",") if match[2] else []
        return []

    def generate_func_call(
        self, return_type: Type, func_call: str, placeholder_var_name: str
    ):
        # <return_type> placeholder_var_name = func_call
        return f"{str(return_type)} {placeholder_var_name} = {func_call};"

    def generate_inline_if(self, if_condition: str, placeholder_var_name: str):
        # bool placeholder_var_name = if_condition
        return f"bool {placeholder_var_name} = {if_condition};"

    def modify_source_line(
        self,
        source_line: str,
        variable_name: str,
        placeholder_variable_name: str,
    ):
        return source_line.replace(variable_name, placeholder_variable_name)

    def safe_replace_if(self, source_line: str, placeholder_variable_name: str):
        """
        If condition might be incorrectly formatted.
        Safeguard against that by forcefully replacing everything inside the IF clause
        """
        # match content inside parentheses
        pattern = r"\((?:[^()]*\([^()]*\)|[^()]+)\)"

        # replace the content inside parentheses with the placeholder
        return re.sub(pattern, f"({placeholder_variable_name})", source_line)

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
        # FIXME: duplicated in patterMatcher
        return result[1] if (result := re.search(r"\[(.*?)\]", variable_name)) else None

    def is_method_over_array(self, variable_name: str):
        """
        Check if .length is being called over array

        Pattern matcher already filtered out all other methods
        """
        return variable_name.split(".")[1] == "length"

    def get_array_type(self, variable_type: Type):
        return str(variable_type).split("[]")[0]

    def retrieve_mapping_types(self, mapping_type: Type):
        pattern = r"mapping\((.*?)\s*=>\s*(.*?)\)"

        if not (match := re.search(pattern, str(mapping_type))):
            return None, None

        return match[1], match[2]

    def sanitize_if_condition(self, if_condition: str):
        pattern = r"\bIF\b(.{%d,})" % 2

        if match := re.search(pattern, if_condition):
            return match[1].strip()
        return None


# export the singleton
optimizerSingleton = Optimizer.get_instance()
