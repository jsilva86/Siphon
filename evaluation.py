from slither.slither import Slither
import os
import shutil
from functools import reduce
import subprocess
from concurrent.futures import ThreadPoolExecutor, wait
import re


def get_file_names(directory, suffix=None):
    file_names = []
    for root, _, files in os.walk(directory):
        for file in files:
            if not suffix:
                file_names.append(os.path.join(root, file))
            elif file.endswith(suffix):
                file_names.append(os.path.join(root, file))
    return file_names


def get_directories(parent_directory):
    directory_names = []
    for entry in os.scandir(parent_directory):
        if entry.is_dir():
            directory_names.append(entry.name)
    return directory_names


def try_compile_and_move():
    file_names = get_file_names("filtered")
    for file in file_names:
        try:
            Slither(file)
            shutil.copy("./" + file, "./compiled")
        except:
            pass


def count(file, curr):
    print("Current file:", file, curr)
    contract_num = 0
    function_num_3 = 0
    function_num_10 = 0
    function_num = 0
    function_nodes = 0

    try:
        slither = Slither(file)
    except:
        print("ERROR:", file)
        return 0, 0

    for contract in slither.contracts:
        print("Contract:", contract.name)
        if contract.is_library or contract.is_interface:
            continue

        contract_num += 1

        for function in contract.functions:
            if function.name.startswith("slither"):
                continue

            if len(function.nodes) <= 3:
                function_num_3 += 1

            if len(function.nodes) <= 10:
                function_num_10 += 1

            function_num += 1
            function_nodes += len(function.nodes)

    return contract_num, function_num, function_num_3, function_num_10, function_nodes


def contracts_and_functions():
    contract_num = 0
    function_num = 0
    function_num_3 = 0
    function_num_10 = 0
    function_nodes = 0

    futures = []

    file_names = get_file_names("compiled")

    with ThreadPoolExecutor() as executor:
        for index, file in enumerate(file_names):
            curr = str(index) + "/" + str(len(file_names))
            futures.append(executor.submit(count, file, curr))

    wait(futures)

    for future in futures:
        (
            result_contract_num,
            result_function_num,
            result_function_num_3,
            result_function_num_10,
            result_function_nodes,
        ) = future.result()
        contract_num += result_contract_num
        function_num += result_function_num
        function_num_3 += result_function_num_3
        function_num_10 += result_function_num_10
        function_nodes += result_function_nodes

    print(
        "Contracts:",
        contract_num,
        "Functions:",
        function_num,
        "Functions (<= 3 lines):",
        function_num_3,
        "Functions (<= 10 lines):",
        function_num_10,
        "Function nodes:",
        function_nodes,
    )


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
    futures = []
    with ThreadPoolExecutor() as executor:
        for index, file in enumerate(file_names):
            curr = str(index) + "/" + str(len(file_names))
            futures.append(executor.submit(run_contract, file, curr))
        wait(futures)


def successfully_executed():
    all_files = get_file_names("compiled")
    executed_files = get_directories("output/compiled")

    total_executed_smart_contracts = 0
    total_executed_functions = 0
    for index, file in enumerate(executed_files):
        print("Current File:", file, str(index) + "/" + str(len(executed_files)))

        executed_smart_contracts = get_directories("output/compiled" + "/" + file)
        total_executed_smart_contracts += len(executed_smart_contracts)

        for executed_smart_contract in executed_smart_contracts:
            executed_functions = get_directories(
                "output/compiled" + "/" + file + "/" + executed_smart_contract
            )
            total_executed_functions += len(executed_functions)

    print(
        "Total files:",
        len(all_files),
        "Executed files:",
        len(executed_files),
        "Executed Smart Contracts:",
        total_executed_smart_contracts,
        "Executed functions:",
        total_executed_functions,
    )


def count_patterns_and_optimized_functions():
    executed_files = get_directories("output/compiled")
    total_optimized_functions = 0
    pattern_list = [
        "REDUNDANT_CODE",
        "OPAQUE_PREDICATE",
        "EXPENSIVE_OPERATION_IN_LOOP",
        "LOOP_INVARIANT_OPERATION",
        "LOOP_INVARIANT_CONDITION",
    ]
    occurrences_count = {pattern: 0 for pattern in pattern_list}

    sorted_by_patterns_dir = "sorted_by_patterns"
    if not os.path.exists(sorted_by_patterns_dir):
        os.makedirs(sorted_by_patterns_dir)

    for index, file in enumerate(executed_files):
        print("Current File:", file, str(index) + "/" + str(len(executed_files)))

        executed_smart_contracts = get_directories("output/compiled" + "/" + file)
        for executed_smart_contract in executed_smart_contracts:
            executed_functions = get_directories(
                "output/compiled" + "/" + file + "/" + executed_smart_contract
            )

            for executed_function in executed_functions:
                optimized_function = get_file_names(
                    "output/compiled"
                    + "/"
                    + file
                    + "/"
                    + executed_smart_contract
                    + "/"
                    + executed_function,
                    ".sol",
                )

                total_optimized_functions += len(optimized_function)
                patterns_file = (
                    "output/compiled"
                    + "/"
                    + file
                    + "/"
                    + executed_smart_contract
                    + "/"
                    + executed_function
                    + "/patterns.txt"
                )

                with open(patterns_file, "r") as f:
                    content = f.read()
                    for pattern in pattern_list:
                        matches = re.findall(pattern, content)
                        occurrences_count[pattern] += len(matches)

                        if matches:
                            pattern_dir = os.path.join(sorted_by_patterns_dir, pattern)

                            if not os.path.exists(pattern_dir):
                                os.makedirs(pattern_dir)

                            sc_func_dir = os.path.join(
                                pattern_dir,
                                file,
                                executed_smart_contract,
                                executed_function,
                            )

                            original_file = os.path.join("compiled", file + ".sol")

                            os.makedirs(sc_func_dir)

                            if optimized_function:
                                shutil.copy(optimized_function[0], sc_func_dir)

                            shutil.copy(patterns_file, sc_func_dir)
                            shutil.copy(original_file, sc_func_dir)

    print("Optimized functions:", total_optimized_functions)
    print("Pattern count:")
    print(occurrences_count)


if __name__ == "__main__":
    # try_compile_and_move()

    # contracts_and_functions()

    # exec_on_func_basis()

    # successfully_executed()

    count_patterns_and_optimized_functions()
