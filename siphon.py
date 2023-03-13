import sys

from lib.slither.slitherSingleton import SlitherSingleton
from lib.cfg_builder.cfg import CFG

def main() -> None:

    # TODO allow for multiple files or dirs to be passed

    slitherSingleton = SlitherSingleton.get_slither_instance()
    slitherSingleton.init_slither_instance(sys.argv[1])
    
    get_cfg_by_function(slitherSingleton)
    

def get_cfg_by_function(slitherSingleton: SlitherSingleton):
    
    # target for analysis
    cfg_by_function = []
    
    functions_by_contract = slitherSingleton.get_functions_by_contract()
    
    for contract_name, functions in functions_by_contract.items():
        # retrieve the original contract information
        contract = slitherSingleton.slither.get_contract_from_name(contract_name)[0] # assume unique name
        for function in functions:
            if function.name == "four":
                cfg = CFG(contract, function).build_cfg()
    
if __name__ == "__main__":
    main()