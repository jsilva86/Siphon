import sys
from lib import SlitherSingleton

def main() -> None:

    # TODO allow for multiple files or dirs to be passed

    slitherInstance = SlitherSingleton.get_slither_instance()
    slitherInstance.init_slither_instance(sys.argv[1])

    contracts = slitherInstance.slither.get_contract_from_name("Test")
    assert len(contracts) == 1
    contract = contracts[0]
    # Get the variable
    test = contract.get_function_from_signature("one()")
    assert test
    nodes = test.nodes

    for node in nodes:
        print("node", node)
        for s in node.ssa_local_variables_written:
            print("local", s)
        for s in node.ssa_state_variables_written:
            print("storage", s)


if __name__ == "__main__":
    main()