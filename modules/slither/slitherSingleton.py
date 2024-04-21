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
            return

        if not self.slither or override:
            self.slither = Slither(target)

    def get_contracts(self) -> List["Contract"]:
        """Returns the contracts in the target file

        Returns:
            list(contracts): List of Contracts
        """
        return list(
            filter(
                lambda contract: not contract.is_library and not contract.is_interface,
                self.slither.contracts,
            )
        )

    def get_contract_by_name(self, contract_name: str) -> Contract:
        """Returns contract with given name

        Returns:
            contract: Contract
        """
        contracts = list(
            filter(
                lambda contract: contract.name == contract_name, self.get_contracts()
            )
        )

        if contracts:
            return contracts[0]  # assume unique contract name

        print("[*] - Contract not found...\n")
        exit()

    def get_function_by_name(self, contract_name: str, function_name: str):
        functions = list(
            filter(
                lambda function: function.name == function_name,
                self.get_all_functions_in_contract(contract_name),
            )
        )

        if functions:
            return functions[0]  # only one function with the given name

        print("[*] - Function not found...\n")
        exit()

    def get_all_functions_in_contract(self, contract_name: str) -> List["Function"]:
        return self.get_functions_by_contract().get(contract_name, [])

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
                            if not fn.name.startswith(
                                "slither"
                            )  # ignore functions injected by slither
                        }
                    )
                }
            )
            or result,
            self.get_contracts(),
            {},
        )


# export the singleton
slitherSingleton = SlitherSingleton.get_slither_instance()
