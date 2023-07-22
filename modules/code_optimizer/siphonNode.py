from slither.core.cfg.node import Node


class SiphonNode:
    """
    Placeholder to hold a reconstructed instruction

    """

    def __init__(self, instruction: Node, expression: str):
        # in the case of new instructions holds the Node that originated it
        self._original_instruction = instruction

        # hold the new/reconstructed instruction
        self._expression = expression

        # mimic Node type
        self._type = "SIPHON_NODE"

        # mimic Node node_id
        self._node_id = -1

    @property
    def original_instruction(self):
        return self._original_instruction

    @property
    def type(self):
        return self._type

    @property
    def node_id(self):
        return self._node_id

    @property
    def expression(self):
        return self._expression

    def __str__(self):
        return self._expression
