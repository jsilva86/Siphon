from typing import List, Dict
from z3 import *

from slither.core.declarations import StructureContract

from symbolicTable import SymbolicTable
from cfg_builder.cfg import CFG

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

    def init_symbolic_table(self, func_args: List["StructureContract"]):
        """Initialise the variables common to all paths
        """
        for arg in func_args:
            self.symbolic_table.update(arg)

    def execute(self, cfg: CFG):
        """Entrypoint for the Symbolic execution

        Executes the CFG starting from the head
        """

        # initialise symbolic table with the function arguments
        func_args = cfg.retrieve_function_args()
        self.init_symbolic_table(func_args)

        # start executing from the initial block
        self.execute_node(cfg, cfg.head, {})

    def check_path_constraints(self):
        # Get the current path constraints
        path_constraints = And(self.path_constraints)

        # Check each branch of the path separately
        for branch in self.branches:
            # Check if the branch is reachable
            branch_constraint = Not(And(self.path_constraints[:len(branch)]))
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
