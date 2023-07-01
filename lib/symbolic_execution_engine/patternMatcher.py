import re
from z3 import *

from slither.core.cfg.node import Node
from slither.core.solidity_types.type import Type
from slither.core.solidity_types.mapping_type import MappingType
from slither.core.solidity_types.array_type import ArrayType

from lib.symbolic_execution_engine.symbolicTable import SymbolicTable, SymbolType


class PatternMatcher:
    def __init__(self):
        # Z3 solver
        self._solver: Solver = Solver()

        # pattern candidates
        self._pattern_candidates: list[Pattern] = {}

        # pattern candidates
        self._patterns: list[Pattern] = {}

    @property
    def solver(self) -> Solver:
        """Returns the Z3 solver

        Returns:
            Solver: Solver
        """
        return self._solver

    # PATTERN 1: Redundant code
    # check if a branch is unsatisfiable (UNSAT)
    def p1_redundant_code(
        self,
        condition,
        path_contraints: list,
    ):
        """
        PATTERN 1: Redundant code

        Check if a branch is unsatisfiable (UNSAT)
        """

        # Get the current path constraints
        # TODO maybe store it directly like this
        path_constraints = And(path_contraints)

        # Check if the branch is reachable
        check_constraint = And(path_constraints, condition)

        solver_result = self.solver.check(check_constraint)

        if solver_result == unsat:
            print("-----PATTERN 1: Redundant Code-----")
            print("  condition -> ", condition)
            print("  constraints -> ", path_contraints)

        return solver_result

    def p2_opaque_predicate(self, condition, path_contraints: list):
        """
        PATTERN 2: Opaque predicates

        Check if the branch condition is redundant
        """

        # check if the branch conditions is a tautologie,
        # by proving that the negation of the implication is unsat
        premise = And(path_contraints)
        implication = Implies(premise, condition)

        solver_result = self.solver.check(Not(implication))

        if solver_result == unsat:
            print("-----PATTERN 2: Opaque Predicate-----")
            print("  condition -> ", condition)
            print("  constraints -> ", path_contraints)

    def p4_expensive_operations_in_loop(
        self,
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
            print("-----PATTERN 4: Expensive operations in a loop-----")
            print("  Variable -> ", variable_name)
            print("  Instruction -> ", instruction)
            print("  Current Scope -> ", loop_scope[-1])
            print("  Scope depth -> ", loop_scope)

    def p6_loop_invariant_condition(
        self, condition, symbolic_table: SymbolicTable, loop_scope: list
    ):
        """
        PATTERN 4: Loop invariant condition

        If inside a loop, check if any of the variables
        is bounded to the current scope
        """

        if not loop_scope:
            return False

        # get symbols in the current scope
        loop_bounded_symbols = symbolic_table.get_symbols_by_scope(loop_scope[-1])

        # check if any of the symbols is present in the condition
        if not any(
            self.is_symbol_in_condition(condition, symbol)
            for symbol in loop_bounded_symbols
        ):
            print("-----PATTERN 6: Loop invariant condition-----")
            print("  condition -> ", condition)
            print("  current loop scope -> ", loop_scope[-1])

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
                # if the key was declared in the current scope, then it's a false positive
                return symbolic_indexable_part.loop_scope != loop_scope[-1]

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

    def condition_contains_loop_variable(
        self, condition, symbolic_table: SymbolicTable, loop_scope: list
    ):
        if not loop_scope:
            return False

        # get symbols in the current scope
        loop_bounded_symbols = symbolic_table.get_symbols_by_scope(loop_scope[-1])

        # check if any of the symbols is present in the condition
        return any(
            self.is_symbol_in_condition(condition, symbol)
            for symbol in loop_bounded_symbols
        )

    def is_symbol_in_condition(self, expr, symbol):
        if isinstance(expr, (ArithRef, BoolRef)):
            for arg in expr.children():
                if self.is_symbol_in_condition(arg, symbol):
                    return True
        return expr == symbol.value


class Pattern:
    def __init__(self):
        pass
