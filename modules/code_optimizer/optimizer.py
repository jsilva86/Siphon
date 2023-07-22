from typing import List, Dict

from slither.core.cfg.node import NodeType, Node

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

        # TODO: get the outside block (possible always the false path) to write back
        # print("scope block", block_of_scope.id, block_of_scope)

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
            placeholder_variable_name = self.generate_placeholder_name(s_variable_name)

            if self.should_generate_instructions(
                placeholder_variable_name, block_of_scope
            ):
                # store placeholder variable and its scope
                self._placeholder_variables[
                    placeholder_variable_name
                ] = block_of_scope.id

                # extract the value of Storage to Memory
                assignment = self.generate_storage_access(
                    variable_type, variable_name, placeholder_variable_name
                )

                # GENERATE Assignment instruction
                assignment_instruction = SiphonNode(pattern.instruction, assignment)

                insert_index = loop_start_index - 1
                # in case the BEGIN_LOOP is the first instruction
                if insert_index < 0:
                    insert_index = 0

                # insert assignment before BEGIN_LOOP in block
                block_of_scope._instructions.insert(
                    insert_index, assignment_instruction
                )

                # write-back the value to Storage after loop
                write_back = self.generate_write_back(
                    variable_name, placeholder_variable_name
                )

                # GENERATE Write-Back instruction
                write_back_instruction = SiphonNode(pattern.instruction, write_back)

                # insert write-back after loop in block (false path)
                block_of_scope._false_path._instructions = [
                    write_back_instruction
                ] + block_of_scope._false_path._instructions

            # REPLACE storage access in line
            # same line can have multiple storage accesses
            modified_source_line = modified_source_line.replace(
                variable_name, placeholder_variable_name
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

    def generate_placeholder_name(self, variable_name: str):
        """
        Generate a dummy variable to extract the value and then write back

        Deals with name collision in the contract and function
        """
        storage_variables = self._cfg.contract.variables
        function_variables = self._cfg.function.variables

        prefix = "sp_"
        suffix = 0
        new_variable_name = prefix + variable_name

        # avoid name collision
        while (
            # new_variable_name in generated_variables or
            new_variable_name in storage_variables
            or new_variable_name in function_variables
        ):
            suffix += 1
            new_variable_name = prefix + variable_name + "_" + str(suffix)

        # TODO: works for list.length / list
        # does not work for same variable in multiple lines since lines will be incorrectly generated
        # TODO maybe separate this by type of variable
        return new_variable_name

    def should_generate_instructions(self, variable_name: str, start_block: Block):
        """
        Ensure that placeholders and write-backs are only generated once.

        Additionally, if a placeholder for the given variable_name
        was already generated in an higher scope don't generate it again
        and avoid writting it back as well
        """
        if not variable_name in self._placeholder_variables:
            return True

        placeholder_scope = self._placeholder_variables.get(variable_name)

        # starting on 'start_block', check if 'placeholder_block' is reachable
        # if it is, then a placeholder was already generate in an higher scope
        current_block = start_block
        while current_block:
            if current_block.id == placeholder_scope:
                print("found placeholder")
                return False

            if not current_block.prev_block:
                break

            current_block = current_block.prev_block

        # if block is not found then placeholder was never generated
        return True

    def generate_storage_access(
        self, variable_type, original_var_name: str, placeholder_var_name: str
    ) -> str:
        # <var_type> placeholder_var_name = original_var_name
        return f"{str(variable_type)} {placeholder_var_name} = {original_var_name}"

    def generate_write_back(self, original_var_name: str, placeholder_var_name: str):
        # original_var_name = placeholder_var_name
        return f"{original_var_name} = {placeholder_var_name}"

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


# export the singleton
optimizerSingleton = Optimizer.get_instance()
