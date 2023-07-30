import argparse
import os

from slither.core.declarations import Function, Contract

from modules.slither.slitherSingleton import slitherSingleton
from modules.cfg_builder.cfg import CFG
from modules.symbolic_execution_engine.seEngine import SymbolicExecutionEngine
from modules.code_optimizer.optimizer import optimizerSingleton
from modules.code_optimizer.codeGenerator import codeGeneratorSingleton
from modules.pattern_matcher.patterns import Pattern


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

    # output dir
    if not os.path.exists("output"):
        os.makedirs("output")

    # Wrapper around Slither
    slitherSingleton.init_slither_instance(filename)

    # Build CFG and find patterns
    patterns = siphon_patterns(contract_name, function_name, export_cfgs)

    # Optimize the resulting CFGs given the found patterns
    optimized_cfgs = optimize_patterns(patterns, export_cfgs)

    # Generate the optimized function code
    generate_source_code(optimized_cfgs, filename)


def siphon_patterns(
    contract_name=None, function_name=None, export_cfgs=False
) -> dict[CFG, list[Pattern]]:
    """
    Returns the mapped patterns per function in each contract
    """

    # maps the patterns per function per contract
    # the CFG provides an hash function that maps to the Contract and Function
    patterns_per_function = {}

    # If contract_name is not provided, execute for all functions inside all contracts
    if contract_name is None:
        for (
            contract_name,
            functions,
        ) in slitherSingleton.get_functions_by_contract().items():
            contract = slitherSingleton.get_contract_by_name(contract_name)
            for function in functions:
                cfg, patterns = analyse_function(contract, function, export_cfgs)
                patterns_per_function[cfg] = patterns

    # If contract_name is provided, but function_name is not, execute for all functions inside contract
    elif function_name is None:
        for function in slitherSingleton.get_all_functions_in_contract(contract_name):
            cfg, patterns = analyse_function(contract, function, export_cfgs)
            patterns_per_function[cfg] = patterns

    else:
        # If both contract_name and function_name are provided, execute for the specific function in the contract
        contract = slitherSingleton.get_contract_by_name(contract_name)
        function = slitherSingleton.get_function_by_name(contract_name, function_name)

        cfg, patterns = analyse_function(contract, function, export_cfgs)
        patterns_per_function[cfg] = patterns

    return patterns_per_function


def analyse_function(contract: Contract, function: Function, export_cfgs=False):
    """
    Finds patterns in a function by constructing a CFG and executing SE on it
    """
    # build the function's CFG
    cfg = CFG(contract, function, export_cfgs)
    cfg.build_cfg()

    # perform SE on the CFG
    se_engine = SymbolicExecutionEngine(cfg)

    # retrieve the found patterns
    return cfg, se_engine.find_patterns()


def optimize_patterns(
    patterns: dict[CFG, list[Pattern]],
    export_cfgs: bool = False,
) -> list[CFG]:
    """
    Returns the optimized list of CFGs
    """

    optimized_cfgs = []

    # init the Optimized module for debug or not
    optimizerSingleton.init_instance(export_cfgs)

    for cfg, patterns in patterns.items():
        # Optimizer
        optimizerSingleton.update_instance(cfg, patterns)

        # Generate the optimized CFG
        optimized_cfg = optimizerSingleton.generate_optimized_cfg()
        optimized_cfgs.append(optimized_cfg)

    return optimized_cfgs


def generate_source_code(optimized_cfgs: list[CFG], filename: str):
    # init Code Generator
    codeGeneratorSingleton.init_instance(filename)

    for optimized_cfg in optimized_cfgs:
        # update the CodeGenerator instance
        codeGeneratorSingleton.update_instance(optimized_cfg)

        # the module internally handles outputing to a file format
        codeGeneratorSingleton.generate_source_code()


if __name__ == "__main__":
    main()
