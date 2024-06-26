from enum import Enum


class PatternType(Enum):
    REDUNDANT_CODE = 1
    OPAQUE_PREDICATE = 2
    EXPENSIVE_OPERATION_IN_LOOP = 4
    LOOP_INVARIANT_OPERATION = 5
    LOOP_INVARIANT_CONDITION = 6


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
    def __init__(
        self, block, instruction, variable, sanitized_variable_name, current_scope
    ):
        super().__init__(block, instruction, PatternType.EXPENSIVE_OPERATION_IN_LOOP)
        # always have a 1-1 match in terms of members
        self._variables = [variable]
        self._sanitized_variables = [sanitized_variable_name]

        self._current_scope = current_scope

    @property
    def variables(self):
        return self._variables

    @property
    def sanitized_variables(self):
        return self._sanitized_variables

    @property
    def current_scope(self):
        return self._current_scope

    def __str__(self):
        output = f"-----PATTERN 4: {self.pattern_type.name}-----\n"
        output += super().__str__()
        output += f"Variables: {self.variables}\n"
        output += f"Sanitized Variables: {self.sanitized_variables}\n"
        output += f"Current Scope: {self.current_scope}\n"
        return output


class LoopInvariantOperationPattern(Pattern):
    def __init__(
        self, block, instruction, function, func_call, func_args, current_scope
    ):
        super().__init__(block, instruction, PatternType.LOOP_INVARIANT_OPERATION)
        self._functions = [function]
        self._func_calls = [func_call]
        self._func_args = func_args
        self._current_scope = current_scope

    @property
    def functions(self):
        return self._functions

    @property
    def func_calls(self):
        return self._func_calls

    @property
    def func_args(self):
        return self._func_args

    @property
    def current_scope(self):
        return self._current_scope

    def __str__(self):
        output = f"-----PATTERN 5: {self.pattern_type.name}-----\n"
        output += super().__str__()
        output += f"Functions: {[function.name for function in self.functions]}\n"
        output += f"Function calls: {list(self.func_calls)}\n"
        output += f"Function args: {list(self.func_args)}\n"
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
