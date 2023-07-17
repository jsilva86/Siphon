from slither.core.cfg.node import Node


class SiphonNode:
    """
    Placeholder to hold a reconstructed instruction

    """

    def __init__(self, instruction: Node):
        self._original_instruction = instruction

    @property
    def original_instruction(self):
        return self._original_instruction
