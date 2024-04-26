from slither.slither import Slither
import os
import shutil
from functools import reduce
import subprocess
from multiprocessing import Pool


def get_file_names(directory):
    file_names = []
    # Iterate through all files and directories in the given directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Append the file name to the list
            file_names.append(os.path.join(root, file))
    return file_names


def try_compile_and_move():
    file_names = get_file_names("filtered")
    for file in file_names:
        try:
            slither = Slither(file)
            # Copy the file to the destination directory
            shutil.copy("./" + file, "./compiled")
        except:
            pass


def run_contract(file, curr):
    print("Current file:", file, curr)

    slither = Slither(file)

    contracts = list(
        filter(
            lambda contract: not contract.is_library and not contract.is_interface,
            slither.contracts,
        )
    )

    function_by_contract = reduce(
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
        contracts,
        {},
    )

    for contract in contracts:
        print("Current contract:", contract.name)
        functions = function_by_contract.get(contract.name, [])

        for function in functions:
            print("Current function:", function.name)
            script_path = "siphon.py"
            try:
                subprocess.run(
                    [
                        "python3",
                        script_path,
                        "-f",
                        file,
                        "-c",
                        contract.name,
                        "-fn",
                        function.name,
                    ],
                    timeout=30,
                )
            except:
                pass


def exec_on_func_basis():
    file_names = get_file_names("compiled")

    with Pool() as pool:
        for index, file in enumerate(file_names):
            curr = str(index + 1) + "/" + str(len(file_names))
            pool.apply_async(run_contract, args=(file, curr))

        pool.close()
        pool.join()


if __name__ == "__main__":
    # try_compile_and_move()

    exec_on_func_basis()
