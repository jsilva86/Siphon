from typing import List

from slither.core.cfg.node import Node

class Block:
    """
    Block class

    """
    def __init__(self):        
        self._instructions : List["Node"] = []
        # variables read/write
        # state variables read
        # true/false/next block
    
    @property
    def instructions(self) -> List["Node"]:
        """Returns the list of instructions

        Returns:
            list(Node): list of instructions
        """
        return list(self._instructions)
    
    def add_instruction(self, instruction: Node):
        pass
    