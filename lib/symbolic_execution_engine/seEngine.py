from typing import List, Dict
from z3 import *

from slither.core.cfg.node import NodeType, Node

from lib.symbolic_execution_engine.symbolicTable import SymbolicTable
from lib.cfg_builder.cfg import CFG
from lib.cfg_builder.block import Block


class SymbolicExecutionEngine:
    def __init__(self, cfg: CFG):
        # Z3 solver
        self._solver: Solver = Solver()

        # CFG being analysed
        self._cfg: CFG = cfg

        # Symbolic table to keep track of the symbolic values of variables
        self._symbolic_table: SymbolicTable = SymbolicTable()

        # Store the current path_contraints
        self._path_constraints: List = []

        # A CFG can have several paths that need to be traversed
        self._paths: List = []

    @property
    def solver(self) -> Solver:
        """Returns the Z3 solver

        Returns:
            Solver: Solver
        """
        return self._solver

    @property
    def cfg(self) -> CFG:
        """Returns the CFG being analysed

        Returns:
            CFG: CFG
        """
        return self._cfg

    @property
    def symbolic_table(self) -> SymbolicTable:
        """Returns the current Symbolic Table state

        Returns:
            Symbolic Table: Symbolic Table of variables
        """
        return self._symbolic_table

    @property
    def path_contraints(self) -> List:
        """Returns the list of current path contraints

        Returns:
            list: path contraints
        """
        return list(self._path_constraints)

    @property
    def paths(self) -> List:
        """Returns the list of branches being explored

        Returns:
            list: branches
        """
        return list(self._paths)

    def init_symbolic_table(self, symbolic_table: SymbolicTable):
        """Initialise the variables common to all paths"""
        for arg in self.cfg.retrieve_function_args():
            symbolic_table.update(arg)

    def execute(self):
        """Entrypoint for the Symbolic execution

        Executes the CFG starting from the head
        """

        # Store Symbolic values for each branch
        symbolic_table: SymbolicTable = SymbolicTable()

        # intialise all of them with the function arguments
        self.init_symbolic_table(symbolic_table)

        # Store the path_contraints for each branch
        path_constraints: List = []

        # start executing from the initial block
        self.execute_block(self.cfg.head, symbolic_table, path_constraints)

    def execute_block(
        self, block: Block, symbolic_table: SymbolicTable, path_contraints: list
    ):
        for instruction in block.instructions:
            traverse_additional_paths = self.evaluate_instruction(
                instruction, symbolic_table, path_contraints
            )

        # this will only happen, at most, once at the end of each block
        # saveguard against executing unreachable blocks
        if traverse_additional_paths:
            (
                should_traverse_true_path,
                should_traverse_false_path,
            ) = traverse_additional_paths

            if should_traverse_true_path:
                # TODO update the path constraints
                self.execute_block(block.true_path, symbolic_table, path_contraints)

            if should_traverse_false_path:
                # TODO update the path constraints
                self.execute_block(block.false_path, symbolic_table, path_contraints)

        elif block.true_path:
            # reached the end of a block
            # go to the next one
            self.execute_block(block.true_path, symbolic_table, path_contraints)

    def evaluate_instruction(
        self, instruction: Node, symbolic_table: SymbolicTable, path_contraints: list
    ):
        match instruction.type:
            case NodeType.IF:
                self.evaluate_if_case(instruction, symbolic_table, path_contraints)

            case _:
                self.evaluate_default_case(instruction, symbolic_table, path_contraints)

    def evaluate_if_case(
        self, instruction: Node, symbolic_table: SymbolicTable, path_contraints: list
    ):
        # TODO check branch constraints and update list
        pass

    def evaluate_default_case(
        self, instruction: Node, symbolic_table: SymbolicTable, path_contraints: list
    ):
        # TODO check for assignments to update symbolic table
        pass

    def check_path_constraints(self):
        # Get the current path constraints
        path_constraints = And(self.path_constraints)

        # Check each branch of the path separately
        for branch in self.branches:
            # Check if the branch is reachable
            branch_constraint = Not(And(self.path_constraints[: len(branch)]))
            check_constraint = And(path_constraints, branch_constraint)

            if self.solver.check(check_constraint) == unsat:
                # If the branch is not reachable, add a negation of its condition to the path constraints
                negation_constraint = Not(branch[-1])
                self.path_constraints.append(negation_constraint)
            else:
                # If the branch is reachable, add its condition to the path constraints
                self.path_constraints.append(branch[-1])

        # Update the symbolic table with the new path constraints
        for variable, value in self.symbolic_table.items():
            self.symbolic_table[variable] = simplify(And(value, path_constraints))

        # Check if any of the symbolic values are unsatisfiable
        for variable, value in self.symbolic_table.items():
            if self.solver.check(value) == unsat:
                print(f"Warning: {variable} has unsatisfiable symbolic value {value}")
