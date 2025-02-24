### Directory Structure
Eval package is independent from the rest of the project. It can be used as a standalone evaluation package.

```shell
leettools/
└── eval/
    ├── pytest.ini
    ├── eval.py
    ├── eval_benchmarks.py
    ├── __init__.py          
    ├── data_preprocess/
    │   ├── __init__.py     
    │   ├── base_dataset.py
    │   └── financebench_loader.py
    └── test/
        ├── __init__.py      
        └── data_preprocess/
            ├── __init__.py  
            └── test_financebench_loader.py
```


#### Configuration
- `pytest.ini`: Configuration file for pytest, sets up Python path and test options

#### Data Processing (`data_preprocess/`)
- `base_dataset.py`: Defines the abstract base class (`BaseDataset`) that all dataset loaders must implement
- `financebench_loader.py`: Implementation of the FinanceBench dataset loader, handles loading and processing of financial benchmark data

#### Tests (`test/`)
- `data_preprocess/`: Contains test files corresponding to the data processing modules
  - `test_financebench_loader.py`: Unit tests for the FinanceBench dataset loader

#### Package Files
- `__init__.py`: Empty files that mark directories as Python packages, enabling proper import functionality

### Key Features
- Modular design for easy addition of new benchmark datasets
- Separate test directory structure mirroring the main package
- Clear separation of concerns between data loading and processing
- Standardized interface through base classes

