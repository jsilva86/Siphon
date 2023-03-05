from typing import List

from slither.core.declarations import Function, Contract

from Block import Block

class CFGBuilder:
    """
    CFGBuilder class

    """

    def __init__(self, contract, function):
        self._contract = contract
        self._function = function
        self._blocks = []
        
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
    
    
    
    
        
    
    
        
    