from slither.core.cfg.node import Node

from modules.slither.slitherSingleton import slitherSingleton


def get_source_line_from_node(instruction: Node):
    # TODO: hardcoded filename...
    # start line of contract:
    # print(get_source_line_from_node(self.cfg._contract))
    return slitherSingleton.slither.crytic_compile.get_code_from_line(
        "sc-examples/Test.sol", instruction.source_mapping.lines[0]
    )
