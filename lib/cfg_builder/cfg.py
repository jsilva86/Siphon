from typing import List

from slither.core.declarations import Function, Contract

from lib.cfg_builder.block import Block

class CFG:
    """
    CFG class

    """
    def __init__(self, contract: Contract, function: Function):
        self._contract: Contract = contract
        self._function: Function = function
        self._blocks: List["Block"] = []
        
    @property
    def function(self) -> Function:
        """Returns the function

        Returns:
            function: function instance
        """
        return list(self._function)
    
    @property
    def contract(self) -> Contract:
        """Returns the contract

        Returns:
            contract: contract instance
        """
        return list(self._contract)
    
    @property
    def blocks(self) -> List["Block"]:
        """Returns the blocks inside a function

        Returns:
            list(blocks): list of blocks
        """
        return list(self._blocks)
    
    
    
    
        
    
    
        
    