from slither.core.cfg.node import Node

from modules.cfg_builder.cfg import CFG
from modules.slither.slitherSingleton import slitherSingleton


class CodeGenerator:
    """
    CodeGenerator class

    """

    instance = None

    _cfg: CFG = None

    @property
    def cfg(self) -> CFG:
        return self._cfg

    @staticmethod
    def get_instance():
        if not CodeGenerator.instance:
            CodeGenerator.instance = CodeGenerator()
        return CodeGenerator.instance

    def update_instance(self, cfg: CFG):
        # optimized CFG
        self._cfg = cfg

    def generate_source_code(self):
        print("aqui")


def get_source_line_from_node(instruction: Node):
    # TODO: hardcoded filename...
    # start line of contract:
    # print(get_source_line_from_node(self.cfg._contract))
    return slitherSingleton.slither.crytic_compile.get_code_from_line(
        "sc-examples/Test.sol", instruction.source_mapping.lines[0]
    )


# export the singleton
codeGeneratorSingleton = CodeGenerator.get_instance()
