import argparse

from slither.core.declarations import Function, Contract

from modules.slither.slitherSingleton import slitherSingleton
from modules.cfg_builder.cfg import CFG
from modules.symbolic_execution_engine.seEngine import SymbolicExecutionEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Function Analyzer")

    # Add command line arguments
    parser.add_argument("-f", "--filename", type=str, help="File name", required=True)
    parser.add_argument("-c", "--contract_name", type=str, help="Contract name")
    parser.add_argument("-fn", "--function_name", type=str, help="Function name")
    parser.add_argument("-e", "--export_cfgs", action="store_true", help="Export CFGs")

    # Parse the command line arguments
    args = parser.parse_args()
    filename, contract_name, function_name, export_cfgs = (
        args.filename,
        args.contract_name,
        args.function_name,
        args.export_cfgs,
    )

    slitherSingleton.init_slither_instance(filename)

    analyse(contract_name, function_name, export_cfgs)


def analyse(contract_name=None, function_name=None, export_cfgs=False):
    # If contract_name is not provided, execute for all functions inside all contracts
    if contract_name is None:
        for (
            contract_name,
            functions,
        ) in slitherSingleton.get_functions_by_contract().items():
            contract = slitherSingleton.get_contract_by_name(contract_name)
            for function in functions:
                patterns = analyse_function(contract, function, export_cfgs)

    # If contract_name is provided, but function_name is not, execute for all functions inside contract
    elif function_name is None:
        for function in slitherSingleton.get_all_functions_in_contract(contract_name):
            patterns = analyse_function(contract, function, export_cfgs)

    else:
        # If both contract_name and function_name are provided, execute for the specific function in the contract
        contract = slitherSingleton.get_contract_by_name(contract_name)
        function = slitherSingleton.get_function_by_name(contract_name, function_name)

        patterns = analyse_function(contract, function, export_cfgs)


def analyse_function(contract: Contract, function: Function, export_cfgs=False):
    # build the function's CFG
    cfg = CFG(contract, function, export_cfgs)
    cfg.build_cfg()

    # perform SE on the CFG
    se_engine = SymbolicExecutionEngine(cfg)

    # retrieve the found patterns
    return se_engine.find_patterns()


if __name__ == "__main__":
    main()
