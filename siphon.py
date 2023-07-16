import argparse

from slither.core.declarations import Function, Contract

from modules.slither.slitherSingleton import slitherSingleton
from modules.cfg_builder.cfg import CFG
from modules.symbolic_execution_engine.seEngine import SymbolicExecutionEngine
from modules.code_optimizer.optimizer import optimizerSingleton


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

    # Wrapper around Slither
    slitherSingleton.init_slither_instance(filename)

    # Build CFG and find patterns
    cfg, patterns = analyse(contract_name, function_name, export_cfgs)

    # Optimizer
    optimizerSingleton.init_instance(function_name, cfg, patterns, export_cfgs)

    # Generate the optimized CFG
    optimized_cfg = optimizerSingleton.generate_optimized_cfg()


def analyse(contract_name=None, function_name=None, export_cfgs=False):
    # If contract_name is not provided, execute for all functions inside all contracts
    if contract_name is None:
        for (
            contract_name,
            functions,
        ) in slitherSingleton.get_functions_by_contract().items():
            contract = slitherSingleton.get_contract_by_name(contract_name)
            for function in functions:
                cfg, patterns = analyse_function(contract, function, export_cfgs)

    # If contract_name is provided, but function_name is not, execute for all functions inside contract
    elif function_name is None:
        for function in slitherSingleton.get_all_functions_in_contract(contract_name):
            cfg, patterns = analyse_function(contract, function, export_cfgs)

    else:
        # If both contract_name and function_name are provided, execute for the specific function in the contract
        contract = slitherSingleton.get_contract_by_name(contract_name)
        function = slitherSingleton.get_function_by_name(contract_name, function_name)

        cfg, patterns = analyse_function(contract, function, export_cfgs)

    return cfg, patterns


def analyse_function(contract: Contract, function: Function, export_cfgs=False):
    # build the function's CFG
    cfg = CFG(contract, function, export_cfgs)
    cfg.build_cfg()

    # perform SE on the CFG
    se_engine = SymbolicExecutionEngine(cfg)

    # retrieve the found patterns
    return cfg, se_engine.find_patterns()


if __name__ == "__main__":
    main()
