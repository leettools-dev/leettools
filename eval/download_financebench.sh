#!/bin/bash

# Set up error handling
set -e  # Exit on any error
set -u  # Exit on undefined variable

# Define paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source the Python config
PYTHON_CONFIG=$(python3 -c "
from pathlib import Path
import sys
sys.path.append('${SCRIPT_DIR}')
from data_preprocess.config import DEFAULT_FINANCEBENCH_PATH
print(DEFAULT_FINANCEBENCH_PATH)
")
DATA_DIR="${PYTHON_CONFIG}"
TEMP_DIR="/tmp/financebench_temp"

# Print status function
print_status() {
    echo "📦 $1"
}

# Cleanup function
cleanup() {
    print_status "Cleaning up temporary files..."
    rm -rf "${TEMP_DIR}"
}

# Set trap for cleanup on script exit
trap cleanup EXIT

# Create directories
print_status "Creating directories..."
mkdir -p "${DATA_DIR}"
mkdir -p "${TEMP_DIR}"

# Clone repository to temp directory
print_status "Cloning FinanceBench repository..."
git clone --depth 1 https://github.com/patronus-ai/financebench.git "${TEMP_DIR}"

# Copy required files
print_status "Copying dataset files..."
cp -r "${TEMP_DIR}/data" "${DATA_DIR}/"
cp -r "${TEMP_DIR}/pdfs" "${DATA_DIR}/"

print_status "Dataset setup complete! Files are located in: ${DATA_DIR}"