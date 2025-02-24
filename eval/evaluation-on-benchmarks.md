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

5. **Optional set up** if you get "No module named 'click'" error:


   - Install torch before installing click to avoid potential wheel support issues.

   ```bash
   uv pip install --no-deps torch
   uv pip install click==8.1.7
   ## or uv add "click==8.1.7"
   ```

## Testing
### Prepare Dataset
1. **Download FinanceBench Dataset**
   ```bash
   # Navigate to the eval directory
   cd leettools/eval
   
   # Make the download script executable
   chmod +x download_financebench.sh
   
   # Run the download script
   ./download_financebench.sh
   ```
   This will:
   - Create a `data/financebench` directory in your eval folder
   - Download the required dataset files from FinanceBench repository
   - Set up the correct directory structure for testing
   
   The dataset will be organized as follows:
   ```
   eval/
   ├── data/
   │   └── financebench/
   │       ├── data/
   │       │   ├── financebench_open_source.jsonl
   │       │   └── financebench_document_information.jsonl
   │       └── pdfs/
   │           └── (pdf files)
   ```

2. **Run Tests**
   ```bash
      # Show basic test results
      pytest test/data_preprocess/test_financebench_loader.py

      # Show detailed test results, -v for verbose
      pytest -v test/data_preprocess/test_financebench_loader.py

      # Show test results with detailed output, -s allows print statements
      pytest -v -s test/data_preprocess/test_financebench_loader.py

      # Run specific test
      pytest test/data_preprocess/test_financebench_loader.py::test_get_questions
      ## pytest test/data_preprocess/test_financebench_loader.py -v -k "test_get_metadata"
   ```

   Expected detailed output:
   
   ```
      ...
      test/data_preprocess/test_financebench_loader.py::test_get_questions 
      Found 150 questions
      Sample question: What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the quest...
      Sample answer: $1577.00...
      Sample sources: length: 1, keys: dict_keys(['evidence_text', 'doc_name', 'evidence_page_num', 'evidence_text_full_page'])
      Sample source document: 3M_2018_10K
      PASSED   
   ```

## Usage
To evaluate a benchmark dataset, use the following command:

```bash
python eval_benchmarks.py -d finance
# python eval_benchmarks.py --domain finance
```


[usage instructions will go here]
<!-- ```bash
python evaluate.py --benchmark finance
```

Replace `finance` with the desired benchmark dataset (e.g., `medical`) to run evaluations on different domains. -->

For financial benchmark evaluation, refer to the [FinanceBench repository](https://github.com/patronus-ai/financebench).

