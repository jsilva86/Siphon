from typing import List, Dict
from z3 import *
import re

from slither.core.cfg.node import NodeType, Node
from slither.core.expressions.expression import Expression

from lib.symbolic_execution_engine.symbolicTable import SymbolicTable
from lib.cfg_builder.cfg import CFG
from lib.cfg_builder.block import Block
from slither.slithir.operations import Operation


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
            symbolic_table.update(arg.name)

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
                self.evaluate_if(instruction, symbolic_table, path_contraints)

            case NodeType.VARIABLE:
                self.evaluate_variable_declaration(
                    instruction, symbolic_table, path_contraints
                )

            case NodeType.EXPRESSION:
                self.evaluate_expression(instruction, symbolic_table, path_contraints)

            case _:
                self.evaluate_default(instruction, symbolic_table, path_contraints)

        # for v in symbolic_table.table.items():
        #     print(v)

    def evaluate_if(
        self, instruction: Node, symbolic_table: SymbolicTable, path_contraints: list
    ):
        # TODO check branch constraints and update list
        if_operation = self.build_if_operation(instruction, symbolic_table)
        print(if_operation)

    def evaluate_expression(
        self, instruction: Node, symbolic_table: SymbolicTable, path_contraints: list
    ):
        if not (parts := self.split_assignment(instruction.expression)):
            # TODO these might be func calls
            return

        variable, operation, assignment = parts

        current_sym_value = symbolic_table.get(variable)

        new_sym_value = self.update_with_prev_value(
            current_sym_value, operation, assignment, symbolic_table
        )

        symbolic_table.update(variable, new_sym_value)

    def evaluate_variable_declaration(
        self, instruction: Node, symbolic_table: SymbolicTable, path_contraints: list
    ):
        # add the value to the symbolic table
        symbolic_table.update(instruction.variable_declaration.name)

        # if the variable is initialised store its value
        if instruction.variable_declaration.expression:
            symbolic_value = self.build_symbolic_value(
                str(instruction.variable_declaration.expression), symbolic_table
            )

            symbolic_table.update(instruction.variable_declaration.name, symbolic_value)

    def evaluate_default(
        self, instruction: Node, symbolic_table: SymbolicTable, path_contraints: list
    ):
        pass

    def check_path_constraints(
        self,
        symbolic_table: SymbolicTable,
        path_contraints: list,
    ):
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

    def build_if_operation(self, instruction: Node, symbolic_table: SymbolicTable):
        # store all operations being made
        operations = {}

        # TMP_XX = <some_operation>
        pattern = r"^([^=\s]+)\s*=\s*(.*)$"

        for ir in instruction.irs:
            # Match the pattern against the string
            match = re.match(pattern, str(ir))

            if not match:
                # When we reach this, the operation as been completed and the value is stored in TMP_XX
                match = re.match(r"CONDITION\s+(.+)", str(ir))

                # Extract the TMP that stores the final value
                key_to_final_value = match[1].strip()

                return operations[key_to_final_value]

            # Extract the temporary variable being used to store and its value
            tmp_var = re.sub(r"\([^()]*\)", "", match[1])  # ignore the type of the TMP
            operation = match[2]

            # complex operands use TMPs to store their values before comparison
            # TMP_14(uint256) = result (c)+ x
            if any(operator in operation for operator in ["+", "-", "*", "/"]):
                # ignore if a variable is constant
                # TODO check if there are more variations
                assignment = operation.replace("(c)", "")

                tmp_assignment = self.build_symbolic_value(assignment, symbolic_table)
                operations[tmp_var] = tmp_assignment
                continue

            # all the other cases are operations
            operator, fn = self.get_operator(operation)

            # the operands can also be TMPs and symbolic values
            first_operand, second_operand = self.resolve_operands(
                operations, operation, operator, symbolic_table
            )

            # apply the operation to the operands
            if operator in ["&&", "||", "!"]:
                # boolean operation
                if not str(first_operand):
                    # Not case only has one operand, the second one
                    operations[tmp_var] = fn(second_operand)
                else:
                    operations[tmp_var] = fn(first_operand, second_operand)
            else:
                # comparison operation
                operations[tmp_var] = self.apply_comparison_operator(
                    first_operand, second_operand, operator
                )

    def resolve_operands(
        self, operations, operation, operator, symbolic_table: SymbolicTable
    ):
        # Split the expression based on the operator
        parts = operation.split(operator)
        first_operand = parts[0].strip()
        second_operand = parts[1].strip()

        # if the operand is a TMP, get its real value
        if self.is_temporary_operand(first_operand):
            first_operand = operations.get(first_operand)

        # check if the value is a symbolic_value
        first_operand = symbolic_table.get(first_operand)

        if self.is_temporary_operand(second_operand):
            second_operand = operations.get(second_operand)

        # check if the value is a symbolic_value
        second_operand = symbolic_table.get(second_operand)

        # return the enhanced operands
        return first_operand, second_operand

    def get_operator(self, operation):
        # Handle comparison operators
        fn = None
        if "<" in operation:
            operator = "<"
        elif ">" in operation:
            operator = ">"
        elif "==" in operation:
            operator = "=="
        elif "<=" in operation:
            operator = "<="
        elif ">=" in operation:
            operator = ">="
        elif "!=" in operation:
            operator = "!="
        elif "&&" in operation:
            operator = "&&"
            fn = And
        elif "||" in operation:
            operator = "||"
            fn = Or
        elif "!" in operation:
            operator = "!"
            fn = Not

        return operator, fn

    def apply_comparison_operator(self, first_operand, second_operand, operator):
        operators = {
            "<": lambda x, y: x < y,
            ">": lambda x, y: x > y,
            "==": lambda x, y: x == y,
            "<=": lambda x, y: x <= y,
            ">=": lambda x, y: x >= y,
            "!=": lambda x, y: x != y,
        }

        return operators[operator](first_operand, second_operand)

    def is_temporary_operand(self, operand: str):
        pattern = r"^TMP_"

        match = re.match(pattern, operand)
        return bool(match)

    def update_with_prev_value(
        self,
        current_sym_value,
        operation: str,
        assignment: str,
        symbolic_table: SymbolicTable,
    ):
        assign_symb_value = self.build_symbolic_value(assignment, symbolic_table)

        if operation == "*=":
            return simplify(current_sym_value * assign_symb_value)
        elif operation == "+=":
            return simplify(current_sym_value + assign_symb_value)
        elif operation == "-=":
            return simplify(current_sym_value - assign_symb_value)
        elif operation == "/=":
            return simplify(current_sym_value / assign_symb_value)
        elif operation == "=":
            return simplify(assign_symb_value)

    def build_symbolic_value(self, expression: str, symbolic_table: SymbolicTable):
        result_list = []

        # find all the tokens in the expressions
        # operations, constants, variables and function calls
        tokens = re.findall(r"\d+|\w+\(?\)?|[+\-*/]", expression)

        # convert all tokens to their correct format
        for token in tokens:
            if token in ["+", "-", "*", "/"]:
                result_list.append(token)
            elif self.is_numeric(token):
                result_list.append(RealVal(token))
            else:
                result_list.append(
                    symbolic_table.get(token)
                )  # if the value is symbolic, return its value

        result = result_list[0]

        # Apply the operations in the list
        for i in range(1, len(result_list), 2):
            operator = result_list[i]
            value = result_list[i + 1]
            if operator == "+":
                result += value
            elif operator == "-":
                result -= value
            elif operator == "*":
                result *= value
            elif operator == "/":
                result /= value

        # return the simplified results
        return simplify(result)

    def is_numeric(self, s: str):
        # help parse out ints and floats from a string
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return None

    def split_assignment(self, expression: Expression):
        # split assignments, like so
        # x += 2
        # x = y + 3
        pattern = r"(\w+)\s*([+\-*/]?=)\s*(.+)"
        if not (match := re.match(pattern, str(expression))):
            return None
        return match[1], match[2], match[3]
