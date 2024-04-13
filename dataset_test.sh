#!/bin/bash

 # Find all .sol files in the search directory and its subdirectories
shopt -s globstar
for file in dataset/*.sol; do
    if [[ -f "$file" ]]; then
        ./siphon.sh -f "$file" -fm
    fi
done