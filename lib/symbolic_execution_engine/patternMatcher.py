import re
from z3 import *
from enum import Enum

from slither.core.cfg.node import Node

from lib.cfg_builder.block import Block
from lib.symbolic_execution_engine.symbolicTable import SymbolicTable, SymbolType
from slither.core.declarations import Function


class PatternType(Enum):
    REDUNDANT_CODE = 1
    OPAQUE_PREDICATE = 2
    EXPENSIVE_OPERATION_IN_LOOP = 4
    LOOP_INVARIANT_CONDITION = 6


class PatternMatcher:
    def __init__(self):
        # Z3 solver
        self._solver: Solver = Solver()

        # pattern candidates
        self._pattern_candidates: dict[int, list[Pattern]] = {}

        # pattern candidates
        self._patterns: list[Pattern] = {}

    @property
    def solver(self) -> Solver:
        """Returns the Z3 solver

        Returns:
            Solver: Solver
        """
        return self._solver

    def __str__(self):
        output = "    *Pattern Candidates*   \n\n"
        for _, patterns in self._pattern_candidates.items():
            for pattern in patterns:
                output += str(pattern)
            output += "\n"
        return output

    def add_pattern_candidate(self, pattern):
        instruction = pattern.instruction
        pattern_type = pattern.pattern_type

        # TODO not this simple for the other patterns
        # same instruction can have multiple storage variables
        if pattern_type in [
            PatternType.REDUNDANT_CODE,
            PatternType.OPAQUE_PREDICATE,
        ]:
            if instruction.node_id in self._pattern_candidates:
                existing_patterns = self._pattern_candidates[instruction.node_id]
                for existing_pattern in existing_patterns:
                    if existing_pattern.pattern_type == pattern_type:
                        return  # Pattern already exists, do not add again

        self._pattern_candidates.setdefault(instruction.node_id, []).append(pattern)

    # PATTERN 1: Redundant code
    # check if a branch is unsatisfiable (UNSAT)
    def p1_redundant_code(
        self,
        block: Block,
        instruction: Node,
        condition,
        path_contraints: list,
    ):
        """
        PATTERN 1: Redundant code

        Check if a branch is unsatisfiable (UNSAT)
        """
        # Get the current path constraints

        check_constraint = condition

        if path_contraints:
            check_constraint = And(*path_contraints, condition)

        is_condition_sat = self.solver.check(check_constraint) == sat

        if not is_condition_sat:
            self.add_pattern_candidate(
                RedundantCodePattern(block, instruction, condition, path_contraints)
            )

        return is_condition_sat

    def p2_opaque_predicate(
        self, block: Block, instruction: Node, condition, path_contraints: list
    ):
        """
        PATTERN 2: Opaque predicates

        Check if the branch condition is redundant
        """

        # check if the branch conditions is a tautology
        # by proving that the negation of the implication is unsat
        premise = And(path_contraints)
        implication = Implies(premise, condition)

        solver_result = self.solver.check(Not(implication))

        if solver_result == unsat:
            self.add_pattern_candidate(
                OpaquePredicatePattern(block, instruction, condition, path_contraints)
            )

    def p4_expensive_operations_in_loop(
        self,
        block: Block,
        instruction: Node,
        variable_name: str,
        loop_scope: list,
        symbolic_table: SymbolicTable,
    ):
        """
        PATTERN 4: Expensive operations in a loop

        Check if a variable ins being read/written to inside a loop
        """
        if (
            self.is_storage_variable_accessed(
                instruction, variable_name, loop_scope, symbolic_table
            )
            and loop_scope
        ):
            self.add_pattern_candidate(
                ExpensiveOperationInLoopPattern(
                    block, instruction, variable_name, loop_scope[-1]
                )
            )

    def p5_loop_invariant_operations(
        self,
        block: Block,
        instruction: Node,
        function_call,
        symbolic_table: SymbolicTable,
        functions: list["Function"],
        loop_scope: int,
    ):
        """
        PATTERN 5: Loop invariant conditions

        If inside a loop, check if any function call
        is dependant on the current scope
        """

        sanitized_function_name, func_args = self.extract_function_info(function_call)

        function = self.get_function_by_name(sanitized_function_name, functions)

        # strict check to avoid side-effects from nested function calls or state changes
        if self.has_internal_calls(function) or not function.pure:
            return

        # no arguments, no internal calls and is pure
        if not func_args:
            print("PATTERN 5")

        # get symbols in the current scope
        loop_bounded_symbols = symbolic_table.get_symbols_by_scope(loop_scope)
        tainted_symbols = symbolic_table.get_tainted_symbols_in_scope(loop_scope)

        # if non of the func args are loop_bounded or where tainted by one, then it's a pattern
        loop_bounded_names = [
            symbol.name for symbol in loop_bounded_symbols + tainted_symbols
        ]
        if all(arg not in loop_bounded_names for arg in func_args):
            print("PATTERN 5", function_call)

    def p6_loop_invariant_condition(
        self,
        block: Block,
        instruction: Node,
        condition,
        symbolic_table: SymbolicTable,
        loop_scope: list,
    ):
        """
        PATTERN 6: Loop invariant conditions

        If inside a loop, check if any of the variables
        is bounded to the current scope
        """

        if not loop_scope:
            return

        # get symbols in the current scope
        loop_bounded_symbols = symbolic_table.get_symbols_by_scope(loop_scope[-1])

        # check if any of the symbols is present in the condition
        # taint checking is not required since we are already analysing the expression
        if not any(
            self.is_symbol_in_condition(condition, symbol)
            for symbol in loop_bounded_symbols
        ):
            self.add_pattern_candidate(
                LoopInvariantConditionPattern(
                    block, instruction, condition, loop_scope[-1]
                )
            )

    def is_storage_variable_accessed(
        self,
        instruction: Node,
        variable_name: str,
        loop_scope: list,
        symbolic_table: SymbolicTable,
    ) -> bool:
        # sourcery skip: remove-unnecessary-cast
        sanitized_variable_name, indexable_part = self.sanitize_variable_name(
            str(variable_name)
        )

        # top-level shallow check for mappings and lists
        # this first condition only asserts that the mapping or list was accessed, but the specific element
        if any(
            s_variable.name == sanitized_variable_name
            for s_variable in instruction.state_variables_written
            + instruction.state_variables_read
        ):
            symbolic_variable = symbolic_table.get_symbol(sanitized_variable_name)

            # always a pattern
            if symbolic_variable.is_primitive():
                return True

            # calling method over list (list.length)
            if symbolic_variable.is_array() and not indexable_part:
                return True

            if symbolic_indexable_part := symbolic_table.get_symbol(indexable_part):
                # if the key was declared or tainted in the current scope,
                # if it was, then it's a false positive and should not be reported
                return (
                    symbolic_indexable_part.loop_scope != loop_scope[-1]
                    and symbolic_indexable_part.taint_scope != loop_scope[-1]
                )

            # most likely a constant value key
            return True

        return False

    def sanitize_variable_name(self, name: str):
        """Sanitize indexable part of variable

        Returns:
            If name contains square brackets: mapping, key
            If name doesn't contain square brackets: variable
        """

        # TODO handle structs
        if result := re.search(r"(\w+)\[(.*?)\]", name):
            return result[1], result[2]

        # ignore everything after "."
        # FIXME probably won't work for structs
        parts = name.split(".")
        return parts[0], None

    def is_symbol_in_condition(self, expr, symbol):
        if isinstance(expr, (ArithRef, BoolRef)):
            for arg in expr.children():
                if self.is_symbol_in_condition(arg, symbol):
                    return True
        return expr == symbol.value

    def extract_function_info(self, function_call):
        pattern = r"(\w+)\((.*)\)"
        if match := re.match(pattern, function_call):
            function_name = match[1]
            arguments = match[2].split(", ") if match[2] else []
            return function_name, arguments

        return None, []

    def get_function_by_name(self, function_name: str, functions: list):
        function = filter(lambda function: function.name == function_name, functions)

        return next(function, None)

    def has_internal_calls(self, function: Function):
        return (
            function.internal_calls
            or function.solidity_calls
            or function.low_level_calls
            or function.high_level_calls
            or function.library_calls
            or function.external_calls_as_expressions
        )

    def are_func_args_loop_bounded(self, loop_bounded_symbols: list, func_args: list):
        loop_bounded_names = [symbol.name for symbol in loop_bounded_symbols]
        return all(arg not in loop_bounded_names for arg in func_args)


class Pattern:
    def __init__(self, block, instruction, pattern_type):
        self._block = block
        self._instruction = instruction
        self._pattern_type = pattern_type

    @property
    def block(self):
        return self._block

    @property
    def instruction(self):
        return self._instruction

    @property
    def pattern_type(self):
        return self._pattern_type

    def __str__(self):
        return f"Block: {self.block.id}\nInstruction: {self.instruction}\n"


class RedundantCodePattern(Pattern):
    def __init__(self, block, instruction, condition, path_constraints):
        super().__init__(block, instruction, PatternType.REDUNDANT_CODE)
        self._condition = condition
        self._path_constraints = path_constraints

    @property
    def condition(self):
        return self._condition

    @property
    def path_constraints(self):
        return self._path_constraints

    def __str__(self):
        output = f"-----PATTERN 1: {self.pattern_type.name}-----\n"
        output += super().__str__()
        output += f"Condition: {self.condition}\n"
        output += f"Path Constraints: {self.path_constraints}\n"
        return output


class OpaquePredicatePattern(Pattern):
    def __init__(self, block, instruction, condition, path_constraints):
        super().__init__(block, instruction, PatternType.OPAQUE_PREDICATE)
        self._condition = condition
        self._path_constraints = path_constraints

    @property
    def condition(self):
        return self._condition

    @property
    def path_constraints(self):
        return self._path_constraints

    def __str__(self):
        output = f"-----PATTERN 2: {self.pattern_type.name}-----\n"
        output += super().__str__()
        output += f"Condition: {self.condition}\n"
        output += f"Path Constraints: {self.path_constraints}\n"
        return output


class ExpensiveOperationInLoopPattern(Pattern):
    def __init__(self, block, instruction, variable, current_scope):
        super().__init__(block, instruction, PatternType.EXPENSIVE_OPERATION_IN_LOOP)
        self._variable = variable
        self._current_scope = current_scope

    @property
    def variable(self):
        return self._variable

    @property
    def current_scope(self):
        return self._current_scope

    def __str__(self):
        output = f"-----PATTERN 4: {self.pattern_type.name}-----\n"
        output += super().__str__()
        output += f"Variable: {self.variable}\n"
        output += f"Current Scope: {self.current_scope}\n"
        return output


class LoopInvariantConditionPattern(Pattern):
    def __init__(self, block, instruction, condition, current_scope):
        super().__init__(block, instruction, PatternType.LOOP_INVARIANT_CONDITION)
        self._condition = condition
        self._current_scope = current_scope

    @property
    def condition(self):
        return self._condition

    @property
    def current_scope(self):
        return self._current_scope

    def __str__(self):
        output = f"-----PATTERN 6: {self.pattern_type.name}-----\n"
        output += super().__str__()
        output += f"Condition: {self.condition}\n"
        output += f"Current Scope: {self.current_scope}\n"
        return output
