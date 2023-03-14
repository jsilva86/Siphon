from typing import List
from random import randint

from slither.core.cfg.node import Node

class Block:
    """
    Block class

    """
    def __init__(self):
        
        # instructions inside the block        
        self._instructions: List["Node"] = []
        
        # paths to follow in case of a new block or branch conditions
        self._true_path: Block = None
        self._false_path: Block = None
        self._prev_block: Block = None

        # TODO maybe aggregate Node information here 
        # variables read/write
        # state variables read
        # true/false/next block
        self._id: int = randint(0,10000)
        
        self._printed: bool = False
    
    def __str__(self):
        return '\n'.join(map(repr, [str(instruction) for instruction in self.instructions]))
    
    @property
    def instructions(self) -> List["Node"]:
        """Returns the list of instructions within this block

        Returns:
            list(Node): list of instructions
        """
        return list(self._instructions)
    
    @property
    def true_path(self) -> "Block":
        """Returns the true path

        Returns:
            Block: Next Block
        """
        return self._true_path
    
    @property
    def false_path(self) -> "Block":
        """Returns the false path

        Returns:
            Block: Next Block
        """
        return self._false_path
    
    @property
    def prev_block(self) -> "Block":
        """Returns the previous Block

        Returns:
            Block: Previous Block
        """
        return self._prev_block
    
    @property
    def id(self) -> int:
        """Returns Block Id

        Returns:
            id: Block Id 
        """
        return self._id
    
    @property
    def printed(self) -> int:
        """Returns if the block was already printed

        Returns:
            printed: Printed
        """
        return self._printed
    
    @instructions.setter
    def instructions(self, value):
        self._instructions.append(value)
        
    @true_path.setter
    def true_path(self, value):
        self._true_path = value
        
    @false_path.setter
    def false_path(self, value):
        self._false_path = value
        
    @prev_block.setter
    def prev_block(self, value):
        self._prev_block = value
        
    @printed.setter
    def printed(self, value):
        self._printed = value
        
    @id.setter
    def id(self, value):
        self._id = value
    
    def add_instruction(self, instruction: Node):
        self._instructions.append(instruction)    