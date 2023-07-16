from typing import List

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

        # return the optimized CFG

        if self.export_cfg:
            cfg_to_dot(f"{self.function_name}-optimized", self.cfg.head)

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
        pass

    def handle_loop_invariant_operation(self, pattern: LoopInvariantOperationPattern):
        pass

    def handle_loop_invariant_condition(self, pattern: LoopInvariantConditionPattern):
        pass


# export the singleton
optimizerSingleton = Optimizer.get_instance()
