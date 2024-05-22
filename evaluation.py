from slither.slither import Slither
import os
import shutil
from functools import reduce
import subprocess
from concurrent.futures import ThreadPoolExecutor, wait, as_completed
import re
import math
import random
import json
import matplotlib.pyplot as plt
import numpy as np

pattern_list = [
    "REDUNDANT_CODE",
    "OPAQUE_PREDICATE",
    "EXPENSIVE_OPERATION_IN_LOOP",
    "LOOP_INVARIANT_OPERATION",
    "LOOP_INVARIANT_CONDITION",
]

detection_occurrences_count = {}
optimized_occurrences_count = {}


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
                ],
                timeout=30,
            )
        except:
            pass

        # for function in functions:
        #     print("Current function:", function.name)
        #     script_path = "siphon.py"
        #     try:
        #         subprocess.run(
        #             [
        #                 "python3",
        #                 script_path,
        #                 "-f",
        #                 file,
        #                 "-c",
        #                 contract.name,
        #                 "-fn",
        #                 function.name,
        #             ],
        #             timeout=30,
        #         )
        #     except:
        #         pass


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


def try_compile_and_move(file):
    command = (
        "npx prettier --plugin=prettier-plugin-solidity --ignore-path .prettierignore "
        + file
    )
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, _ = process.communicate()
    if process.returncode != 0:
        return False

    path = file.split(os.path.sep)
    new_file_path = os.path.sep.join(path[1:])
    os.makedirs(os.path.sep.join(["optimized_and_compiled"] + path[1:-1]))
    path = os.path.join("optimized_and_compiled", new_file_path)

    with open(path, "wb") as f:
        f.write(stdout)
        return True


def compile_optimized():
    pattern_dirs = get_directories("sorted_by_patterns")

    optimized_and_compiled_dir = "optimized_and_compiled"
    os.makedirs(optimized_and_compiled_dir, exist_ok=True)

    for pattern in pattern_list:
        os.makedirs(os.path.join(optimized_and_compiled_dir, pattern), exist_ok=True)

    # for pattern_dir in pattern_dirs:
    #     pattern_path = os.path.join("sorted_by_patterns", pattern_dir)
    #     optimized_files = get_directories(pattern_path)

    #     for index, optimized_file in enumerate(optimized_files):
    #         print(
    #             "Current File",
    #             optimized_file,
    #             str(index + 1) + "/" + str(len(optimized_files) - 1),
    #             pattern_dir,
    #         )

    #         optimized_file_path = os.path.join(pattern_path, optimized_file)
    #         optimized_smart_contracts = get_directories(optimized_file_path)

    #         for optimized_smart_contract in optimized_smart_contracts:
    #             optimized_smart_contract_path = os.path.join(
    #                 optimized_file_path, optimized_smart_contract
    #             )
    #             optimized_functions = get_directories(optimized_smart_contract_path)

    #             for optimized_function in optimized_functions:
    #                 optimized_function_path = os.path.join(
    #                     optimized_smart_contract_path, optimized_function
    #                 )

    #                 optimized_function_file = get_file_names(
    #                     optimized_function_path,
    #                     "-optimized.sol",
    #                 )

    #                 if not optimized_function_file or not try_compile_and_move(
    #                     optimized_function_file[0]
    #                 ):
    #                     continue

    #                 path = optimized_function_path.split(os.path.sep)
    #                 path = os.path.join(
    #                     "sorted_by_patterns", os.path.sep.join(path[1:])
    #                 )

    #                 patterns_file = os.path.join(path, "patterns.txt")
    #                 original_file = os.path.join(path, optimized_file + ".sol")

    #                 dir = optimized_function_file[0].split(os.path.sep)
    #                 new_dir = os.path.sep.join(dir[1:-1])
    #                 dir = os.path.join("optimized_and_compiled", new_dir)

    #                 shutil.copy(patterns_file, dir)
    #                 shutil.copy(original_file, dir)

    print("Counting...")
    occurrences_count = {pattern: 0 for pattern in pattern_list}

    for pattern_dir in pattern_dirs:
        if pattern_dir == "EXPENSIVE_OPERATION_IN_LOOP_bad":
            continue
        pattern_path = os.path.join("optimized_and_compiled", pattern_dir)
        optimized_files = get_directories(pattern_path)

        for index, optimized_file in enumerate(optimized_files):
            optimized_file_path = os.path.join(pattern_path, optimized_file)
            optimized_smart_contracts = get_directories(optimized_file_path)

            for optimized_smart_contract in optimized_smart_contracts:
                optimized_smart_contract_path = os.path.join(
                    optimized_file_path, optimized_smart_contract
                )
                optimized_functions = get_directories(optimized_smart_contract_path)

                for optimized_function in optimized_functions:
                    optimized_function_path = os.path.join(
                        optimized_smart_contract_path, optimized_function
                    )

                    patterns_file = get_file_names(optimized_function_path, ".txt")

                    optimized_function_file = get_file_names(
                        optimized_function_path,
                        "-optimized.sol",
                    )

                    if not optimized_function_file or not patterns_file:
                        continue

                    with open(patterns_file[0], "r") as f:
                        content = f.read()
                        for pattern in pattern_list:
                            matches = re.findall(pattern, content)
                            occurrences_count[pattern] += len(matches)

    print(
        "Optimized + Compiled Patterns:",
        occurrences_count,
    )

    optimized_occurrences_count = occurrences_count


def cochran_sample_size(population_size):
    z = 1.96  # confidence level 95%
    margin_of_error = 0.05
    p = 0.5  # population proportion

    sample_size = (z**2 * (0.25)) / (margin_of_error**2)
    adjusted_sample_size = sample_size / (1 + ((sample_size - 1) / population_size))

    return math.ceil(adjusted_sample_size)


def pick_from_sample(population_size):
    sample_size = cochran_sample_size(population_size)

    numbers = list(range(1, population_size + 1))
    random.shuffle(numbers)
    selected_numbers = numbers[:sample_size]
    return selected_numbers


def detection_sampling():
    pattern_dirs = get_directories("sorted_by_patterns")

    occurrences_count = {pattern: {} for pattern in pattern_list}

    for pattern_dir in pattern_dirs:
        start_index = 0
        end_index = 0
        prev_file = None

        pattern_path = os.path.join("sorted_by_patterns", pattern_dir)
        optimized_files = get_directories(pattern_path)

        for optimized_file in optimized_files:
            optimized_file_path = os.path.join(pattern_path, optimized_file)
            optimized_smart_contracts = get_directories(optimized_file_path)

            for optimized_smart_contract in optimized_smart_contracts:
                optimized_smart_contract_path = os.path.join(
                    optimized_file_path, optimized_smart_contract
                )
                optimized_functions = get_directories(optimized_smart_contract_path)

                for optimized_function in optimized_functions:
                    optimized_function_path = os.path.join(
                        optimized_smart_contract_path, optimized_function
                    )

                    patterns_file = get_file_names(optimized_function_path, ".txt")

                    optimized_function_file = get_file_names(
                        optimized_function_path,
                        "-optimized.sol",
                    )

                    if not optimized_function_file or not patterns_file:
                        continue

                    with open(patterns_file[0], "r") as f:
                        content = f.read()

                        matches = re.findall(pattern_dir, content)

                        if not matches:
                            continue

                        end_index += len(matches)

                        if prev_file is None:
                            start_index = 0
                        else:
                            start_index = (
                                occurrences_count[pattern_dir][prev_file][1] + 1
                            )

                        occurrences_count[pattern_dir][optimized_function_path] = (
                            start_index,
                            end_index,
                        )

                    prev_file = optimized_function_path

    # print("Intervals:")
    # for pattern_dir, optimized_functions in occurrences_count.items():
    #     print(f"Pattern Directory: {pattern_dir}")
    #     for optimized_function_path, (
    #         start_index,
    #         end_index,
    #     ) in optimized_functions.items():
    #         print(f"  Optimized Function Path: {optimized_function_path}")
    #         print(f"    Start Index: {start_index}, End Index: {end_index}")

    chosen_patterns = {pattern: [] for pattern in pattern_list}
    detection_occurrences_count = {
        "REDUNDANT_CODE": 147,
        "OPAQUE_PREDICATE": 131,
        # "EXPENSIVE_OPERATION_IN_LOOP": 2382,
        "LOOP_INVARIANT_OPERATION": 2,
        "LOOP_INVARIANT_CONDITION": 259,
    }
    for detection_occurence in detection_occurrences_count.keys():

        pattern_count = detection_occurrences_count[detection_occurence]
        sampled_elements = pick_from_sample(pattern_count)

        for sampled_element in sampled_elements:
            keys = list(occurrences_count[detection_occurence].keys())
            low = 0
            high = len(keys) - 1

            while low <= high:
                mid = (low + high) // 2
                file_key = keys[mid]
                interval = occurrences_count[detection_occurence][file_key]
                if interval[0] <= sampled_element <= interval[1]:
                    chosen_patterns[detection_occurence].append(
                        {"file": file_key, "index": sampled_element - interval[0]}
                    )
                    break
                elif sampled_element < interval[0]:
                    high = mid - 1
                else:
                    low = mid + 1

    print(chosen_patterns)

    with open("detection_sample_v2", "w") as json_file:
        json.dump(chosen_patterns, json_file)


def coersion_fix_executor(pattern_dir):
    pattern_path = os.path.join("sorted_by_patterns", pattern_dir)
    optimized_files = get_directories(pattern_path)

    for index, optimized_file in enumerate(optimized_files):
        print(f"Current file - {pattern_dir}: {index + 1} / {len(optimized_files)}")
        optimized_file_path = os.path.join(pattern_path, optimized_file)
        optimized_smart_contracts = get_directories(optimized_file_path)

        for optimized_smart_contract in optimized_smart_contracts:
            optimized_smart_contract_path = os.path.join(
                optimized_file_path, optimized_smart_contract
            )
            optimized_functions = get_directories(optimized_smart_contract_path)

            for optimized_function in optimized_functions:
                original_file_path = os.path.join(
                    optimized_file_path,
                    optimized_smart_contract,
                    optimized_function,
                    optimized_file + ".sol",
                )

                script_path = "siphon.py"
                try:
                    subprocess.run(
                        [
                            "python3",
                            script_path,
                            "-f",
                            original_file_path,
                            "-c",
                            optimized_smart_contract,
                            "-fn",
                            optimized_function,
                        ],
                        timeout=30,
                    )
                except:
                    pass


def coersion_fix():
    pattern_dirs = get_directories("sorted_by_patterns")

    futures = []
    with ThreadPoolExecutor() as executor:
        for index, pattern in enumerate(pattern_dirs):
            futures.append(executor.submit(coersion_fix_executor, pattern))
        wait(futures)


def generate_find_charts():
    patterns = [
        "Redundant code",
        "Opaque predicate",
        "Expensive operation inside loop",
        "Loop invariant operation",
        "Loop invariant condition",
    ]

    false_positives = [
        89,
        98,
        172,
        2,
        124,
    ]

    correct = [
        107 - 89,
        0,
        330 - 172,
        0,
        155 - 124,
    ]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    bars1 = ax.barh(
        patterns,
        false_positives,
        align="center",
        height=0.25,
        color="orange",
        label="False positives",
    )
    bars2 = ax.barh(
        patterns,
        correct,
        align="center",
        height=0.25,
        left=false_positives,
        color="blue",
        label="Correct",
    )

    for bar1, bar2 in zip(bars1, bars2):
        total = bar1.get_width() + bar2.get_width()
        ax.text(
            total,
            bar1.get_y() + bar1.get_height() / 2,
            f"{total:.0f}",
            ha="left",
            va="center",
            color="black",
        )

    ax.set_yticks(patterns)
    ax.set_xlabel("Occurrences")
    ax.legend()
    ax.set_xlim(right=max(false_positives) + max(correct) + 50)

    plt.tight_layout()
    plt.savefig("detected_patterns.png")

    def rc():
        fig, ax = plt.subplots(figsize=(10, 5), subplot_kw=dict(aspect="equal"))

        def func(pct, allvals):
            absolute = int(np.round(pct / 100.0 * np.sum(allvals)))
            return f"{pct:.1f}%\n({absolute:d} occurrences)"

        data = [44, 28, 9, 7]
        ingredients = [
            "Ternary operators",
            "Return value coercion",
            "Global state",
            "Other",
        ]

        wedges, texts, autotexts = ax.pie(
            data, autopct=lambda pct: func(pct, data), textprops=dict(color="w")
        )

        ax.legend(
            wedges,
            ingredients,
            title="Type",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
        )

        plt.setp(autotexts, size=8, weight="bold")
        plt.tight_layout()
        plt.savefig(
            "false_positives_distribution_rc.png", bbox_inches="tight", pad_inches=0.1
        )

    def op():

        data = [70, 10, 10, 8]
        ingredients = [
            "Return value coercion",
            "Global state",
            "Approximated loop iterations",
            "Other",
        ]

        fig, ax = plt.subplots(figsize=(10, 5), subplot_kw=dict(aspect="equal"))

        def func(pct, allvals):
            absolute = int(np.round(pct / 100.0 * np.sum(allvals)))
            return f"{pct:.1f}%\n({absolute:d} occurrences)"

        wedges, texts, autotexts = ax.pie(
            data, autopct=lambda pct: func(pct, data), textprops=dict(color="w")
        )

        ax.legend(
            wedges,
            ingredients,
            title="Type",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
        )

        plt.setp(autotexts, size=8, weight="bold")
        plt.tight_layout()
        plt.savefig(
            "false_positives_distribution_op.png", bbox_inches="tight", pad_inches=0.1
        )

    def eol():

        data = [132, 27, 11, 3]
        ingredients = [
            "Non-linear control flow",
            "Loop scope",
            "Loop-dependent objects",
            "Other",
        ]

        fig, ax = plt.subplots(figsize=(10, 5), subplot_kw=dict(aspect="equal"))

        def func(pct, allvals):
            absolute = int(np.round(pct / 100.0 * np.sum(allvals)))
            return f"{pct:.1f}%\n({absolute:d} occurrences)"

        wedges, texts, autotexts = ax.pie(
            data, autopct=lambda pct: func(pct, data), textprops=dict(color="w")
        )

        ax.legend(
            wedges,
            ingredients,
            title="Type",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
        )

        plt.setp(autotexts, size=8, weight="bold")
        plt.tight_layout()

        plt.savefig(
            "false_positives_distribution_eol.png", bbox_inches="tight", pad_inches=0.1
        )

    def lic():

        data = [51, 58, 10, 5]
        ingredients = [
            "Loop-dependent variables",
            "Return value coercion",
            "Loop scope",
            "Other",
        ]

        fig, ax = plt.subplots(figsize=(10, 5), subplot_kw=dict(aspect="equal"))

        def func(pct, allvals):
            absolute = int(np.round(pct / 100.0 * np.sum(allvals)))
            return f"{pct:.1f}%\n({absolute:d} occurrences)"

        wedges, texts, autotexts = ax.pie(
            data, autopct=lambda pct: func(pct, data), textprops=dict(color="w")
        )

        ax.legend(
            wedges,
            ingredients,
            title="Type",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
        )

        plt.setp(autotexts, size=8, weight="bold")
        plt.tight_layout()

        plt.savefig(
            "false_positives_distribution_lic.png", bbox_inches="tight", pad_inches=0.1
        )

    rc()
    op()
    eol()
    lic()


def generate_optimized_charts():
    # Data
    elements = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    gas_used_normal = [
        595031,
        1075680,
        1556496,
        2037457,
        2518575,
        2999848,
        3481278,
        3962864,
        4444606,
        4926504,
    ]
    gas_used_optimized = [
        576465,
        1040614,
        1504930,
        1969391,
        2434009,
        2898782,
        3363712,
        3828798,
        4294040,
        4759438,
    ]
    percent_saved = [3.12, 3.26, 3.31, 3.34, 3.36, 3.37, 3.38, 3.38, 3.39, 3.39]

    # Calculate the width of the bars
    bar_width = 0.35

    # Calculate the x-axis positions for the bars
    x = np.arange(len(elements))

    np.std(gas_used_normal)

    # Plot
    plt.figure(figsize=(12, 6))

    # Plot gas used by normal version
    bars1 = plt.plot(
        x,
        gas_used_normal,
        label="Original",
    )

    # Plot gas used by optimized version
    bars2 = plt.plot(
        x,
        gas_used_optimized,
        label="Optimised",
    )

    # Add x-axis labels
    plt.xlabel("Number of iterations")
    plt.ylabel("Gas Used")

    # Add title
    # plt.title("Gas used per number of iterations")

    # Add x-axis ticks and labels
    plt.xticks(x, elements)

    # Add legend
    plt.legend()

    plt.savefig("loop_invariant_optimisation.png", bbox_inches="tight", pad_inches=0.1)

    # Data for gas usage
    iterations = [100, 200, 300, 400, 500]
    gas_tokenRescue = [66413, 108713, 151013, 193313, 235613]
    gas_tokenRescue_optimized = [55672, 87184, 118684, 150184, 181684]

    # Calculate percentage savings
    percentage_savings = [
        ((original - optimized) / original) * 100
        for original, optimized in zip(gas_tokenRescue, gas_tokenRescue_optimized)
    ]

    # Plotting the lines for gas usage
    plt.figure(figsize=(10, 6))
    plt.plot(iterations, gas_tokenRescue, label="Original", marker="o")
    plt.plot(iterations, gas_tokenRescue_optimized, label="Optimised", marker="o")
    plt.xlim(50, 550)
    for i, (x, y, percent) in enumerate(
        zip(iterations, gas_tokenRescue_optimized, percentage_savings)
    ):
        plt.text(
            x,
            y,
            f"- {percent:.2f}%",
            fontsize=12,
            verticalalignment="top",
            horizontalalignment="left",
        )

    # Adding labels and title
    plt.xlabel("Number of iterations")
    plt.ylabel("Gas Used")
    plt.legend()

    plt.savefig(
        "expensive_operation_len_optimisation.png", bbox_inches="tight", pad_inches=0.1
    )


if __name__ == "__main__":
    # # to filter contracts that don't compile with Solidty version 0.8.0
    # try_compile_and_move()

    # # gather dataset statistics
    # contracts_and_functions()

    # # exec Siphon on the dataset
    # exec_on_func_basis()

    # coersion_fix()

    # # gather analysis statistics
    # successfully_executed()

    # # count detected patterns
    # count_patterns_and_optimized_functions()

    # # count optimized patterns
    # compile_optimized()

    # detection sampling
    # detection_sampling()

    # generate_find_charts()

    generate_optimized_charts()
