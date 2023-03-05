import sys
from lib import SlitherSingleton
from slither.core.declarations.contract import Contract, Function


def main() -> None:

    # TODO allow for multiple files or dirs to be passed

    slitherInstance = SlitherSingleton.get_slither_instance()
    slitherInstance.init_slither_instance(sys.argv[1])
    
    res = slitherInstance.get_functions_by_contract()
    
    for key in res:
        print("----",key)
        for func in res[key]:
            print(">", func.full_name)
            for node in func.nodes:
                print(node)
    
    
if __name__ == "__main__":
    main()