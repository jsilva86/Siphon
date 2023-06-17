from typing import List, Dict
from z3 import *
import re
from copy import deepcopy

from slither.core.cfg.node import NodeType, Node
from slither.core.expressions.expression import Expression
from slither.core.solidity_types.type import Type
from slither.core.solidity_types.array_type import ArrayType
from slither.core.solidity_types.mapping_type import MappingType

from lib.symbolic_execution_engine.symbolicTable import SymbolicTable, SymbolType
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
            symbol_type = self.get_symbol_type(arg.type)
            symbolic_table.push_symbol(arg.name, symbol_type)

        for variable in self.cfg.retrieve_storage_variables():
            symbol_type = self.get_symbol_type(variable.type)
            # add the value to the symbolic table
            symbolic_table.push_symbol(variable.name, symbol_type)

            # if the variable is initialised store its value
            if variable.expression:
                symbolic_value = self.build_symbolic_value(
                    str(variable.expression), symbolic_table
                )

                symbolic_table.update_symbol(variable.name, symbolic_value)

    def execute(self):
        """Entrypoint for the Symbolic execution

        Executes the CFG starting from the head
        """

        # Store Symbolic values for each branch
        symbolic_table: SymbolicTable = SymbolicTable()

        # intialise the symbolic table with the function arguments and storage variables
        self.init_symbolic_table(symbolic_table)

        # Store the path_contraints for each branch
        path_constraints: List = []

        # Store the identifiers of the loops
        loop_scope: List = []

        # start executing from the initial block
        self.execute_block(self.cfg.head, symbolic_table, path_constraints, loop_scope)

    def execute_block(
        self,
        block: Block,
        symbolic_table: SymbolicTable,
        path_contraints: list,
        loop_scope: list,
    ):
        for instruction in block.instructions:
            traverse_additional_paths = self.evaluate_instruction(
                block, instruction, symbolic_table, path_contraints, loop_scope
            )

        # this will only happen, at most, once at the end of each block
        # saveguard against executing unreachable blocks
        if traverse_additional_paths:
            self.unpack_and_execute_next_block(
                traverse_additional_paths,
                block,
                symbolic_table,
                path_contraints,
                loop_scope,
            )
        elif block.true_path:
            # reached the end of a block
            # go to the next one
            self.execute_block(
                block.true_path, symbolic_table, path_contraints, loop_scope
            )

    def unpack_and_execute_next_block(
        self,
        traverse_additional_paths: dict,
        block: Block,
        symbolic_table: SymbolicTable,
        path_contraints: list,
        loop_scope: list,
    ):
        """
        Avoid executing unreachable paths
        """

        should_traverse_true_path = traverse_additional_paths.get(
            "should_traverse_true_path"
        )

        true_path_constraint = traverse_additional_paths.get("true_path_constraint")

        should_traverse_false_path = traverse_additional_paths.get(
            "should_traverse_false_path"
        )

        false_path_constraint = traverse_additional_paths.get("false_path_constraint")

        # fork both paths
        new_path_constraints = deepcopy(path_contraints)
        new_symbolic_table = deepcopy(symbolic_table)
        new_loop_scope = deepcopy(loop_scope)

        if should_traverse_true_path:
            new_path_constraints.append(true_path_constraint)
            self.execute_block(
                block.true_path,
                new_symbolic_table,
                new_path_constraints,
                new_loop_scope,
            )

        if should_traverse_false_path and block.false_path:
            # else case is optional
            new_path_constraints.append(false_path_constraint)
            self.execute_block(
                block.false_path,
                new_symbolic_table,
                new_path_constraints,
                new_loop_scope,
            )

    def evaluate_instruction(
        self,
        block: Block,
        instruction: Node,
        symbolic_table: SymbolicTable,
        path_contraints: list,
        loop_scope: list,
    ):
        match instruction.type:
            case NodeType.IF:
                return self.evaluate_if(
                    instruction, symbolic_table, path_contraints, loop_scope
                )

            case NodeType.VARIABLE:
                self.evaluate_variable_declaration(instruction, symbolic_table)

            case NodeType.EXPRESSION:
                self.evaluate_expression(instruction, symbolic_table, loop_scope)

            case NodeType.STARTLOOP:
                self.evaluate_begin_loop(
                    block, instruction, symbolic_table, path_contraints, loop_scope
                )

            case NodeType.IFLOOP:
                return self.evaluate_if_loop(
                    block, instruction, symbolic_table, path_contraints, loop_scope
                )

            case NodeType.ENDLOOP:
                return self.evaluate_end_loop(
                    block, instruction, symbolic_table, path_contraints, loop_scope
                )

            case _:
                self.evaluate_default(instruction, symbolic_table, path_contraints)

    def evaluate_if(
        self,
        instruction: Node,
        symbolic_table: SymbolicTable,
        path_contraints: list,
        loop_scope: list,
    ):
        if_operation = self.build_if_operation(instruction, symbolic_table, loop_scope)
        if_not_operation = Not(if_operation)
        print("-----Analising IF-----")
        print("  Operation -> ", if_operation)
        print("  Constraints -> ", path_contraints)

        # PATTERN 1: Redundant code
        # check if any of the branches are unsatisfiable

        is_true_path_sat = self.check_path_constraints(if_operation, path_contraints)
        is_false_path_sat = self.check_path_constraints(
            if_not_operation, path_contraints
        )

        print("  Is if sat -> ", is_true_path_sat)
        print("  Is else sat -> ", is_false_path_sat)

        # PATTERN 2: Opaque predicates
        # check if any of the branch conditions are tautologies,
        # prove that the negation of the implication is unsat

        premise = And(path_contraints)

        if_implication = Implies(premise, if_operation)
        if_not_implication = Implies(premise, if_not_operation)

        is_if_opaque = self.solver.check(Not(if_implication)) == unsat
        is_if_not_opaque = self.solver.check(Not(if_not_implication)) == unsat

        print("  Is if Opaque -> ", is_if_opaque)
        print("  Is else Opaque -> ", is_if_not_opaque)

        return {
            "should_traverse_true_path": is_true_path_sat,
            "should_traverse_false_path": is_false_path_sat,
            "true_path_constraint": if_operation,
            "false_path_constraint": if_not_operation,
        }

    def evaluate_expression(
        self, instruction: Node, symbolic_table: SymbolicTable, loop_scope: list
    ):
        if not (parts := self.split_assignment(instruction.expression)):
            # TODO these might be func calls
            # TODO does not work for structs and list index assignments
            print("Unable to resolve assignment", instruction)
            return

        variable, operation, assignment = parts

        # HACK: avoid changing symbolic value of loop bound variable when stepping
        if instruction.sons[0].type == NodeType.IFLOOP:
            return

        # PATTERN 4: Expensive operations in a loop
        # check if a storage variable is being written to inside a loop
        self.check_storage_accesses(instruction, variable, loop_scope)

        current_sym_value = symbolic_table.get_symbol_value(variable)

        new_sym_value = self.update_with_prev_value(
            current_sym_value,
            operation,
            assignment,
            symbolic_table,
            instruction,
            loop_scope,
        )

        symbolic_table.update_symbol(variable, new_sym_value)

    def evaluate_variable_declaration(
        self, instruction: Node, symbolic_table: SymbolicTable
    ):
        # add the value to the symbolic table
        symbol_Type = self.get_symbol_type(instruction.variable_declaration.type)
        symbolic_table.push_symbol(instruction.variable_declaration.name, symbol_Type)

        # HACK: avoid giving a value to loop bounded variables
        if (
            instruction.sons[0]
            and instruction.sons[0].type == NodeType.STARTLOOP
            and instruction.sons[0].sons[0]
            and instruction.sons[0].sons[0].type == NodeType.IFLOOP
        ):
            return

        # if the variable is initialised store its value
        if instruction.variable_declaration.expression:
            symbolic_value = self.build_symbolic_value(
                str(instruction.variable_declaration.expression), symbolic_table
            )

            symbolic_table.update_symbol(
                instruction.variable_declaration.name, symbolic_value
            )

    def evaluate_begin_loop(
        self,
        block: Block,
        instruction: Node,
        symbolic_table: SymbolicTable,
        path_contraints: list,
        loop_scope: list,
    ):
        # psuh current scope
        loop_scope.append(block.id)

    def evaluate_end_loop(
        self,
        block: Block,
        instruction: Node,
        symbolic_table: SymbolicTable,
        path_contraints: list,
        loop_scope: list,
    ):
        # pop the current scope
        loop_scope.pop()

    def evaluate_if_loop(
        self,
        block: Block,
        instruction: Node,
        symbolic_table: SymbolicTable,
        path_contraints: list,
        loop_scope: list,
    ):
        if_operation = self.build_if_operation(instruction, symbolic_table, loop_scope)

        is_true_path_sat = self.check_path_constraints(if_operation, path_contraints)

        # only traverse loop body once
        should_traverse_loop = is_true_path_sat and not block.visited

        # FIXME: after executing the loop, the constraint might not need to be propagated
        if_not_operation = Not(if_operation)

        # to avoid loops
        is_visited = block.visited
        block.visited = True
        # FIXME: since we are only stopping the loop from happening, all instructions prior will still be executed again
        return {
            "should_traverse_true_path": should_traverse_loop,
            "should_traverse_false_path": not is_visited,  # only exit out of loop once
            "true_path_constraint": if_operation,
            "false_path_constraint": if_not_operation,
        }

    def evaluate_default(
        self, instruction: Node, symbolic_table: SymbolicTable, path_contraints: list
    ):
        print("default inst", instruction, path_contraints)
        pass

    def check_path_constraints(
        self,
        branch_condition,
        path_contraints: list,
    ):
        # Get the current path constraints
        # TODO maybe store it directly like this
        path_constraints = And(path_contraints)

        # Check if the branch is reachable
        check_constraint = And(path_constraints, branch_condition)

        return self.solver.check(check_constraint) == sat

    def build_if_operation(
        self, instruction: Node, symbolic_table: SymbolicTable, loop_scope: list
    ):
        # store all operations being made
        operations = {}

        # TMP_XX = <some_operation>
        pattern = r"^(.*?)\s*=\s*(.*?)$"

        for ir in instruction.irs:
            split = str(ir).split("=", 1)

            if len(split) < 2:
                # When we reach this, the operation as been completed and the value is stored in TMP_XX
                match = re.match(r"CONDITION\s+(.+)", str(ir))

                # Extract the TMP that stores the final value
                key_to_final_value = match[1].strip()

                return operations[key_to_final_value]

            # Extract the temporary variable being used to store and its value
            var = split[0].strip()
            operation = split[1].strip()

            tmp_var = re.sub(r"\([^()]*\)", "", var)  # ignore the type of the TMP
            operation = re.sub(r"\([^()]*\)", "", operation)  # ignore all var types

            # complex operands use TMPs to store their values before comparison
            # TMP_14(uint256) = result (c)+ x + TMP_13(uint256)
            if any(operator in operation for operator in ["+", "-", "*", "/", "%"]):
                # ignore if a variable is constant
                # TODO check if there are more variations
                assignment = operation.replace("(c)", "")

                pattern = r"TMP_\w+"
                matches = re.findall(pattern, assignment)

                for match in matches:
                    if match in operations:
                        assignment = assignment.replace(match, str(operations[match]))

                # tmp_assignment = self.build_symbolic_value(assignment, symbolic_table)

                operations[tmp_var] = assignment
                continue

            # all the other cases are operations
            operator, fn = self.get_operator(operation)

            # the operands can also be TMPs and symbolic values
            first_operand, second_operand = self.resolve_operands(
                operations, operation, operator, symbolic_table, instruction, loop_scope
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
        self,
        operations,
        operation,
        operator,
        symbolic_table: SymbolicTable,
        instruction: Node,
        loop_scope: list,
    ):  # sourcery skip: extract-duplicate-method
        # Split the expression based on the operator
        parts = operation.split(operator)
        first_operand = parts[0].strip()
        second_operand = parts[1].strip()

        # if the operand is a TMP, get its real value
        if self.is_temporary_operand(first_operand):
            first_operand = operations.get(first_operand)

        # PATTERN 4: Expensive operations in a loop
        # check if first_operand is a storage variable

        # FIXME NOT WORKING
        self.check_storage_accesses(instruction, first_operand, loop_scope)

        # check if the value is a symbolic_value
        if any(
            operator in str(first_operand) for operator in ["+", "-", "*", "/", "%"]
        ) and all(
            operator not in str(first_operand)
            for operator in ["<", "<=", ">=", "==", "!=", "&&", "||", "!"]
        ):
            # result (c)+ x + TMP_13(uint256), but not normal comparisons (those are handled outside)
            first_operand = self.build_symbolic_value(
                first_operand, symbolic_table, instruction, loop_scope
            )
        else:
            # standalone value
            first_operand = symbolic_table.get_symbol_value(first_operand)

        if self.is_temporary_operand(second_operand):
            second_operand = operations.get(second_operand)

        # PATTERN 4: Expensive operations in a loop
        # check if second_operand is a storage variable
        self.check_storage_accesses(instruction, second_operand, loop_scope)

        # check if the value is a symbolic_value
        if any(
            operator in str(second_operand) for operator in ["+", "-", "*", "/", "%"]
        ) and all(
            operator not in str(second_operand)
            for operator in ["<", "<=", ">=", "==", "!=", "&&", "||", "!"]
        ):
            # result (c)+ x + TMP_13(uint256), but not normal comparisons (those are handled outside)
            second_operand = self.build_symbolic_value(
                second_operand, symbolic_table, instruction, loop_scope
            )
        else:
            # standalone value
            second_operand = symbolic_table.get_symbol_value(second_operand)

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
        instruction: Node,
        loop_scope: list,
    ):
        assign_symb_value = self.build_symbolic_value(
            assignment, symbolic_table, instruction, loop_scope
        )

        if operation == "*=":
            return simplify(current_sym_value * assign_symb_value)
        elif operation == "+=":
            return simplify(current_sym_value + assign_symb_value)
        elif operation == "-=":
            return simplify(current_sym_value - assign_symb_value)
        elif operation == "/=":
            return simplify(current_sym_value / assign_symb_value)
        elif operation == "%=":
            return simplify(current_sym_value % assign_symb_value)
        elif operation == "=":
            return simplify(assign_symb_value)

    def build_symbolic_value(
        self,
        expression: str,
        symbolic_table: SymbolicTable,
        instruction: Node = None,
        loop_scope: list = None,
    ):
        if loop_scope is None:
            loop_scope = []

        result_list = []

        # find all the tokens in the expressions
        # operations, constants, variables and function calls
        tokens = re.findall(r"\d+|\w+\(?\)?|[+\-*/%]", expression)

        # convert all tokens to their correct format
        for token in tokens:
            if token in ["+", "-", "*", "/", "%"]:
                result_list.append(token)
            elif self.is_numeric(token):
                result_list.append(RealVal(token))
            else:
                # PATTERN 4: Expensive operations in a loop
                # check if a storage variable is being read in assignment
                if instruction:
                    self.check_storage_accesses(instruction, token, loop_scope)

                result_list.append(
                    symbolic_table.get_symbol_value(token)
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
            elif operator == "%":
                result %= value

        # return the simplified results
        return simplify(result)

    def is_numeric(self, s: str):
        try:
            # Attempt to parse the string as an integer or float
            float(s)
            return True
        except ValueError:
            return False

    def split_assignment(self, expression: Expression) -> tuple[str, str, str]:
        """Splits all types of assignments

        x = y + 3

        x -= 10

        x++

        Returns: variable, operator, assignment

        """
        expression_str = str(expression)

        # handle assignments and assignments with operators
        pattern = r"(\w+)\s*([+\-*/]?=)\s*(.+)"
        if match := re.match(pattern, expression_str):
            variable, operator, assignment = match.groups()
            return variable, operator, assignment

        # handle increment(++) and decrement(--)
        pattern = r"(\w+)\s*(\+\+|--)"
        if match := re.match(pattern, expression_str):
            variable, operator = match.groups()
            # convert to standard format
            if operator == "++":
                return variable, "+=", "1"
            if operator == "--":
                return variable, "-=", "1"

        return None

    def check_storage_accesses(
        self, instruction: Node, variable_name: str, loop_scope: list
    ):
        if self.is_storage_variable_accessed(instruction, variable_name) and loop_scope:
            print("-----STATE VARIABLE ACCESSED IN LOOP-----")
            print("  Variable -> ", variable_name)
            print("  Instruction -> ", instruction)
            print("  Current Scope -> ", loop_scope[-1])
            print("  Scope depth -> ", loop_scope)
            # TODO: create report here
            return True
        return False

    def is_storage_variable_accessed(
        self, instruction: Node, variable_name: str
    ) -> bool:
        # sourcery skip: remove-unnecessary-cast
        return any(
            s_variable.name == str(variable_name)
            for s_variable in instruction.state_variables_written
            + instruction.state_variables_read
        )

    def get_symbol_type(self, slither_type: Type):
        if isinstance(slither_type, MappingType):
            return SymbolType.MAPPING
        elif isinstance(slither_type, ArrayType):
            return SymbolType.ARRAY

        return SymbolType.PRIMITIVE
