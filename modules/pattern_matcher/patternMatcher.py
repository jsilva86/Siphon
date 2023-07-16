import re
from z3 import *

from slither.core.cfg.node import Node
from slither.core.declarations import Function

from modules.cfg_builder.block import Block
from modules.symbolic_execution_engine.symbolicTable import SymbolicTable, SymbolType
from modules.pattern_matcher.patterns import *


class PatternMatcher:
    def __init__(self):
        # Z3 solver
        self._solver: Solver = Solver()

        # pattern candidates. Debug purposes
        self._pattern_candidates: list[Pattern] = []

        # pattern candidates
        self._patterns: list[Pattern] = []

    @property
    def solver(self) -> Solver:
        """Returns the Z3 solver

        Returns:
            Solver: Solver
        """
        return self._solver

    def __str__(self):
        # output = "    *Pattern Candidates*   \n\n"
        # for pattern in self._pattern_candidates:
        #     output += str(pattern)
        # output += "\n\n"

        output = "                *Patterns*               \n\n"
        for pattern in self._patterns:
            output += str(pattern)
        output += "\n"
        return output

    # PATTERN 1: Redundant code
    # check if a branch is unsatisfiable (UNSAT)
    def p1_redundant_code(
        self,
        block: Block,
        instruction: Node,
        condition,
        path_contraints: list,
        skip_pattern=False,  # avoid adding patterns for false paths
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

        if not skip_pattern and not is_condition_sat:
            pattern = RedundantCodePattern(
                block, instruction, condition, path_contraints
            )
            # debug
            self._pattern_candidates.append(pattern)

            if not self.is_duplicate_pattern(block, instruction):
                self._patterns.append(pattern)

        return is_condition_sat

    def p2_opaque_predicate(
        self,
        block: Block,
        instruction: Node,
        condition,
        path_contraints: list,
        skip_pattern=False,  # avoid adding patterns for false paths
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

        if not skip_pattern and solver_result == unsat:
            pattern = OpaquePredicatePattern(
                block, instruction, condition, path_contraints
            )
            # debug
            self._pattern_candidates.append(pattern)

            if not self.is_duplicate_pattern(block, instruction):
                self._patterns.append(pattern)

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
            existing_pattern = self.get_pattern_by_instruction_and_type(
                instruction, PatternType.EXPENSIVE_OPERATION_IN_LOOP
            )

            pattern = ExpensiveOperationInLoopPattern(
                block, instruction, variable_name, loop_scope[-1]
            )

            if not existing_pattern:
                self._patterns.append(pattern)

            # ensure that each variable is only flagged once per instruction
            elif variable_name not in existing_pattern.variables:
                existing_pattern.variables.append(variable_name)

            # debug
            self._pattern_candidates.append(pattern)

    def p5_loop_invariant_operations(
        self,
        block: Block,
        instruction: Node,
        function_call,
        symbolic_table: SymbolicTable,
        functions: list["Function"],
        loop_scope: list,
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

        # get symbols in the current scope
        loop_bounded_symbols = symbolic_table.get_symbols_by_scope(loop_scope[-1])
        tainted_symbols = symbolic_table.get_tainted_symbols_in_scope(loop_scope[-1])

        # if none of the func args are loop_bounded or where tainted by one, then it's a pattern
        loop_bounded_names = [
            symbol.name for symbol in loop_bounded_symbols + tainted_symbols
        ]

        # no arguments, no internal calls and function is pure
        # OR
        # none of the func args are loop_bounded or where tainted by one
        if not func_args or all(arg not in loop_bounded_names for arg in func_args):
            existing_pattern = self.get_pattern_by_instruction_and_type(
                instruction, PatternType.LOOP_INVARIANT_CONDITION
            )

            pattern = LoopInvariantOperationPattern(
                block, instruction, function, loop_scope[-1]
            )

            if not existing_pattern:
                self._patterns.append(pattern)

            # ensure that each function is only flagged once per instruction
            elif sanitized_function_name not in [
                function.name for function in existing_pattern.functions
            ]:
                existing_pattern.functions.append(function)

            # debug
            self._pattern_candidates.append(pattern)

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
            pattern = LoopInvariantConditionPattern(
                block, instruction, condition, loop_scope[-1]
            )
            # debug
            self._pattern_candidates.append(pattern)

            if not self.is_duplicate_pattern(block, instruction):
                self._patterns.append(pattern)

    def remove_false_positives(self):
        """
        Some False Positives are only detectable after the analysis is done

        Such is the case for P1/P2: a branch is only "really" unreachable,
        if no path is able to reach it OR is "always" reachable if all branches reach it


        """

        # TODO extend this function to other patterns if needed

        # if a block is reachable via at least one path, then it's a false positive P1
        # if a block is NOT reachable via at least one path, then it's a false positive P2
        self._patterns = list(
            filter(
                lambda pattern: (
                    pattern.pattern_type != PatternType.REDUNDANT_CODE
                    and pattern.pattern_type != PatternType.OPAQUE_PREDICATE
                )
                or (
                    pattern.pattern_type == PatternType.REDUNDANT_CODE
                    and not any(pattern.block._reachability)
                )
                or (
                    pattern.pattern_type == PatternType.OPAQUE_PREDICATE
                    and all(pattern.block._reachability)
                ),
                self._patterns,
            )
        )

    def is_duplicate_pattern(self, block: Block, instruction: Node):
        """
        Check if the instruction/block already has a P1/P2

        If an IF block is a P1, then the ELSE block is always a P2

        Avoid flagging P6 multiple times
        """

        for pattern in self._patterns:
            # this works because each block can only have a P1 or P2
            if (
                pattern.instruction.node_id == instruction.node_id
                or pattern.block.id == block.id
            ):
                if pattern.pattern_type in [
                    PatternType.REDUNDANT_CODE,
                    PatternType.OPAQUE_PREDICATE,
                    PatternType.LOOP_INVARIANT_CONDITION,
                ]:
                    return True
        return False

    def get_pattern_by_instruction_and_type(
        self, instruction: Node, pattern_type: PatternType
    ):
        filtered_patterns = filter(
            lambda pattern: pattern.instruction.node_id == instruction.node_id
            and pattern.pattern_type == pattern_type,
            self._patterns,
        )
        return next(
            filtered_patterns, None
        )  # Return the first matching pattern or None if not found

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

    def get_function_by_name(self, function_name: str, functions: list) -> Function:
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