import os
import shutil


def process_file(file_path, filtered_dir):
    new_file_path = os.path.join(filtered_dir, os.path.basename(file_path))
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    with open(new_file_path, "w", encoding="utf-8") as new_file:
        for line in lines:
            if line.strip().startswith("pragma solidity"):
                # Replace the line with 'pragma solidity 0.8.0;'
                line = "pragma solidity 0.8.0;\n"
            new_file.write(line)

    print(f"Created new file {new_file_path} with modified pragma")


def filter_directory(source_dir, filtered_dir):
    os.makedirs(filtered_dir, exist_ok=True)

    for filename in os.listdir(source_dir):
        if filename.endswith(".sol"):
            file_path = os.path.join(source_dir, filename)
            process_file(file_path, filtered_dir)


if __name__ == "__main__":
    source_directory = "dataset"
    filtered_directory = "filtered"

    filter_directory(source_directory, filtered_directory)
