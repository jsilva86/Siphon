from typing import List

from modules.cfg_builder.cfg import CFG, cfg_to_dot
from modules.symbolic_execution_engine.patternMatcher import Pattern


class Optimizer:
    """
    OptimizerSingleton class

    """

    instance = None

    def __init__(
        self, function_name, cfg: CFG, patterns: List["Pattern"], export_cfg=False
    ) -> None:
        self._function_name: str = function_name

        self._cfg: CFG = cfg

        self._patterns: List["Pattern"] = patterns

        # debug optimized CFG
        self._export_cfg: bool = export_cfg

    @property
    def function_name(self) -> str:
        return self._function_name

    @property
    def cfg(self) -> CFG:
        return self._cfg

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

    def generate_optimized_cfg(self):
        if self.export_cfg:
            cfg_to_dot(f"{self.function_name}-optimized")

        # return the optimized CFG
        return None


# export the singleton
optimizerSingleton = Optimizer.get_instance()
