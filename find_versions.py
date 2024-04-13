# import os
# import re
# from collections import defaultdict

# # Function to find and count occurrences of lines starting with "pragma solidity"
# def process_file(file_path, pragma_count):
#     with open(file_path, 'r', encoding='utf-8') as file:
#         for line in file:
#             if line.strip().startswith('pragma solidity'):
#                 pragma_count[line.strip()] += 1

# # Main function to iterate through files in the directory
# def process_directory(directory_path):
#     pragma_count = defaultdict(int)

#     for filename in os.listdir(directory_path):
#         if filename.endswith('.sol'):
#             file_path = os.path.join(directory_path, filename)
#             process_file(file_path, pragma_count)

#     return pragma_count

# # Function to save results to a text file
# def save_results(result_dict, output_file):
#     with open(output_file, 'w', encoding='utf-8') as file:
#         for line, count in result_dict.items():
#             file.write(f'{line}: {count}\n')

# if __name__ == "__main__":
#     # Replace 'your_dataset_path' and 'output_file.txt' with your actual directory path and desired output file name
#     dataset_path = 'dataset'
#     output_file_name = 'versions.txt'
#     output_file_path = os.path.join(dataset_path, output_file_name)

#     # Process the directory and get the results
#     result_dict = process_directory(dataset_path)

#     # Save the results to a text file
#     save_results(result_dict, output_file_path)

import os
import shutil

def process_file(file_path, filtered_dir):
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip().startswith('pragma solidity') and 'pragma solidity ^0.8.0;' in line:
                # Move the file to the 'filtered' directory
                shutil.move(file_path, os.path.join(filtered_dir, os.path.basename(file_path)))
                print(f'Moved {file_path} to {filtered_dir}')
                break  # Stop processing the file once the condition is met

def filter_directory(source_dir, filtered_dir):
    os.makedirs(filtered_dir, exist_ok=True)

    for filename in os.listdir(source_dir):
        if filename.endswith('.sol'):
            file_path = os.path.join(source_dir, filename)
            process_file(file_path, filtered_dir)

if __name__ == "__main__":
    # Replace 'your_dataset_path' and 'filtered' with your actual directory paths
    source_directory = 'dataset'
    filtered_directory = 'filtered'

    filter_directory(source_directory, filtered_directory)