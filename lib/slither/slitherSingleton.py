from functools import reduce
from typing import List, Dict

from slither.slither import Slither
from slither.core.declarations import Function, Contract

class SlitherSingleton:
    """
    SlitherSingleton class

    """
    instance = None

    def __init__(self) -> None:
        self.slither = None

    @staticmethod
    def get_slither_instance():
        if not SlitherSingleton.instance:
            SlitherSingleton.instance = SlitherSingleton()
        return SlitherSingleton.instance
    
    def init_slither_instance(self, target: str, override: bool = False):
        if not target:
            print("this should an exception")

        if not self.slither or override:
            self.slither = Slither(target)
            
    def get_contracts(self) -> List["Contract"]:
        """Returns the contracts in the target file

        Returns:
            list(contracts): List of Contracts
        """
        return self.slither.contracts  
    
    def get_functions_by_contract(self) -> Dict[str, List["Function"]]:
        """Returns a mapping of each contract to its functions

        Returns:
            dict(contract.name, functions): Dict of functions by contract
        """
        return reduce(
            lambda result, contract: result.update(
                {
                    contract.name: list(
                        {
                            fn
                            for fn in contract.functions
                            if fn.full_name != "slitherConstructorVariables()"  # to ignore the constructor
                        }
                    )
                }
            )
            or result,
            self.get_contracts(),
            {},
        )