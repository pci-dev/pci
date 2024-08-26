#!/bin/bash

# Define the original and new values
original_pdflatex="/home/peercom/texlive/bin/x86_64-linux/pdflatex"
new_compiler="/var/www/peercommunityin/texlive/bin/x86_64-linux/lualatex"

# Check if the file exists
if [ ! -f $1 ]; then
    echo "Error: $1 file not found."
    exit 1
fi

sed -i "s|\pdflatex = $original_pdflatex|compiler = $new_compiler|" $1

echo "File modification completed successfully."
echo "$original_pdflatex -> $new_compiler"
