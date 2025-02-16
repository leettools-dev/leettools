## Description
Eval package provides a structured approach to evaluating Retrieval-Augmented Generation (RAG) systems across multiple benchmark datasets. The benchmarks include financial, medical, and other domain-specific datasets that assess the accuracy and reliability of the RAG pipeline.

Each dataset consists of:
- A collection of PDF documents.
- A set of queries corresponding to each document.
- Desired answers derived from the PDFs.

The evaluation framework supports assessing both individual processing stages (e.g., document retrieval, response generation) and the overall system performance.

## Table of Contents
1. [Installation](#installation)
2. [Usage](#usage)

## Installation
To set up the environment for benchmark evaluation, follow these steps:

1. **Use [uv](https://github.com/astral-sh/uv) for package management** to ensure a clean and efficient environment setup. The environment should be initialized in the [root directory](../) where `dev-requirements.txt` is located.

2. **Create a new virtual environment** in your project directory. This will generate a `.venv` directory within your project folder:
   ```bash
   uv venv
   ```

3. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies** from `dev-requirements.txt`:
   ```bash
   # Install your current project in editable mode (the -e . part). The . refers to the current directory and will make Python treat your project as an installed package
   uv pip install -r dev-requirements.txt -e .
   ```

5. **Optional set up** if you directly run eval from the very begining:

   - Install torch before installing click to avoid potential wheel support issues.

   ```bash
   uv pip install --no-deps torch
   uv pip install click==8.1.7
   ## or uv add "click==8.1.7"
   ```

## Usage
To evaluate a benchmark dataset, use the following command:

[usage instructions will go here]
<!-- ```bash
python evaluate.py --benchmark finance
```

Replace `finance` with the desired benchmark dataset (e.g., `medical`) to run evaluations on different domains. -->

For financial benchmark evaluation, refer to the [FinanceBench repository](https://github.com/patronus-ai/financebench).

