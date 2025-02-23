from pathlib import Path

import pandas as pd
import pytest

from eval.data_preprocess.config import DEFAULT_FINANCEBENCH_PATH
from eval.data_preprocess.financebench_loader import FinanceBenchDataset


@pytest.fixture(scope="session")
def dataset():
    """Fixture to provide an initialized FinanceBenchDataset instance.
    scope="session" ensures the dataset is initialized only once per test session.
    """
    print("\nInitializing FinanceBenchDataset (this should happen only once)")
    return FinanceBenchDataset()

def test_data_file_paths():
    """Test if data files exist at expected locations"""
    # Check if the data directory exists
    data_dir = DEFAULT_FINANCEBENCH_PATH / "data"
    assert data_dir.exists(), f"Data directory not found at {data_dir}"
    
    # Check specific files
    questions_file = data_dir / "financebench_open_source.jsonl"
    meta_file = data_dir / "financebench_document_information.jsonl"
    
    assert questions_file.exists(), f"Questions file not found at {questions_file}"
    assert meta_file.exists(), f"Metadata file not found at {meta_file}"

def test_load_data_basic(dataset):
    """Test basic data loading functionality"""
    # Test if DataFrames are loaded correctly
    assert dataset.questions_df is not None, "Questions DataFrame should not be None"
    assert dataset.meta_df is not None, "Metadata DataFrame should not be None"
    assert isinstance(dataset.questions_df, pd.DataFrame), "questions_df should be a DataFrame"
    assert isinstance(dataset.meta_df, pd.DataFrame), "meta_df should be a DataFrame"

def test_load_data_content(dataset):
    """Test if loaded data contains expected columns and data"""
    # Test questions DataFrame
    assert 'question' in dataset.questions_df.columns, "Questions DataFrame should have 'question' column"
    assert 'answer' in dataset.questions_df.columns, "Questions DataFrame should have 'answer' column"
    assert len(dataset.questions_df) > 0, "Questions DataFrame should not be empty"
    
    # Test metadata DataFrame
    assert 'company' in dataset.meta_df.columns, "Metadata DataFrame should have 'company' column"
    assert 'doc_type' in dataset.meta_df.columns, "Metadata DataFrame should have 'doc_type' column"
    assert len(dataset.meta_df) > 0, "Metadata DataFrame should not be empty"

def test_get_document_paths(dataset):
    """Test getting document paths from the dataset"""
    paths = dataset.get_document_paths()
    
    assert len(paths) > 0, "No PDF documents found"
    assert all(isinstance(p, Path) for p in paths), "All paths should be Path objects"
    assert all(p.suffix == ".pdf" for p in paths), "All files should be PDFs"
    assert all(p.exists() for p in paths), "All paths should exist"
    
    print(f"\nFiltered {len(paths)} PDF documents that are used by verified questions")
    print(f"Sample path: {paths[0]}")

def test_get_questions(dataset):
    """Test getting questions from the dataset"""
    questions = dataset.get_questions()
    
    assert len(questions) > 0, "No questions found"
    for q in questions:
        assert hasattr(q, 'question'), "Question missing 'question' attribute"
        assert hasattr(q, 'expected_answer'), "Question missing 'expected_answer' attribute"
        assert hasattr(q, 'expected_sources'), "Question missing 'expected_sources' attribute"
        assert hasattr(q, 'source_document'), "Question missing 'source_document' attribute"
        assert isinstance(q.question, str), "Question should be string"
        assert isinstance(q.expected_answer, str), "Answer should be string"
        assert isinstance(q.expected_sources, list), "Sources should be a list"
        assert len(q.expected_sources) > 0, "Sources should not be empty"
        assert isinstance(q.source_document, str), "Source document should be string"

        from eval.data_preprocess.base_dataset import AnswerSource

        # Check first evidence
        first_evidence = q.expected_sources[0]
        assert isinstance(first_evidence, AnswerSource), "Evidence should be AnswerSource instance"
    print(f"\nFound {len(questions)} questions")
    print(f"Sample question: {questions[0].question[:100]}...")
    print(f"Sample answer: {questions[0].expected_answer[:100]}...")
    print(f"Sample sources: length: {len(questions[0].expected_sources)}, keys: {questions[0].expected_sources[0].keys()}")
    print(f"Sample source document: {questions[0].source_document}")

    # Print unique document names
    unique_docs = set(q.source_document for q in questions)
    print(f"\nUnique document names ({len(unique_docs)}):")
    # for doc in sorted(unique_docs):
    #     print(f"- {doc}")

def test_get_metadata(dataset):
    """Test getting metadata from the dataset"""
    metadata = dataset.get_metadata()
    
    required_keys = ['total_questions', 'total_documents', 'companies', 'doc_types']
    for key in required_keys:
        assert key in metadata, f"Missing required key: {key}"
    
    assert metadata['total_questions'] > 0, "Should have questions"
    assert metadata['total_documents'] > 0, "Should have documents"
    assert isinstance(metadata['companies'], list), "Companies should be a list"
    assert isinstance(metadata['doc_types'], list), "Document types should be a list"
    
    print("\nMetadata summary:")
    for key, value in metadata.items():
        if isinstance(value, list):
            print(f"{key}: {len(value)} items")
        else:
            print(f"{key}: {value}")
