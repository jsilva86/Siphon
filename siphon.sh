#!/bin/bash

# Function to show the usage of the script
function usage() {
    echo "Usage: $0 -f <filename> [-c <contract_name>] [-fn <function_name>] [-e] [-v] [-fm]"
    exit 1
}

# Function to run prettier for solidity files
function format_files() {
    local search_dir="output"

    # Find all .sol files in the search directory and its subdirectories
    shopt -s globstar
    for file in "$search_dir"/**/*.sol; do
        if [[ -f "$file" ]]; then
            if [[ -n "$verbose" ]]; then
                echo
                echo "> Formatting: $file"

                npx prettier --write --plugin=prettier-plugin-solidity --ignore-path .prettierignore "$file"
            else
                # Suppress the output
                npx prettier --write --plugin=prettier-plugin-solidity --ignore-path .prettierignore  "$file" > /dev/null
            fi
        fi
    done

    if [[ -n "$verbose" ]]; then
        echo
    fi
}

# Check if any arguments were passed
if [[ $# -eq 0 ]]; then
    usage
fi

# Initialize variables
filename=""
contract_name=""
function_name=""
export_cfgs=""
verbose=""
format=""

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -f|--filename)
            filename="$2"
            shift
            ;;
        -c|--contract_name)
            contract_name="$2"
            shift
            ;;
        -fn|--function_name)
            function_name="$2"
            shift
            ;;
        -e|--export_cfgs)
            export_cfgs="true"
            ;;
        -v|--verbose)
            verbose="true"
            ;;
        -fm|--format)
            format="true"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
    shift
done

# Check if the filename argument is provided
if [[ -z "$filename" ]]; then
    echo "File name is required."
    usage
fi

# Build the arguments array for the Python script
python_args=("-f" "$filename")
[[ -n "$contract_name" ]] && python_args+=("-c" "$contract_name")
[[ -n "$function_name" ]] && python_args+=("-fn" "$function_name")
[[ -n "$export_cfgs" ]] && python_args+=("-e")
[[ -n "$verbose" ]] && python_args+=("-v")

# Execute the Python program with the provided arguments
python3 siphon.py "${python_args[@]}"

# Check if format argument is provided
if [[ -n "$format" ]]; then
    if [[ -n "$verbose" ]]; then
        echo "[*] - Formatting files..."
    fi

    # Execute the prettier command
    format_files
    if [[ -n "$verbose" ]]; then
        echo "[*] - Finished formatting files..."
    fi
fi