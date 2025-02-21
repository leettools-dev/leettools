import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from eval.data_preprocess.financebench_loader import FinanceBenchDataset


@pytest.fixture
def sample_data():
    # Create sample data for testing
    questions_data = [
        {
            "question": "What was the revenue in 2022?",
            "answer": "The revenue in 2022 was $100M"
        },
        {
            "question": "Who is the CEO?",
            "answer": "John Doe is the CEO"
        }
    ]
    
    meta_data = [
        {
            "company": "TechCorp",
            "doc_type": "10-K",
            "year": 2022
        },
        {
            "company": "TechCorp",
            "doc_type": "10-Q",
            "year": 2022
        }
    ]
    
    return questions_data, meta_data


@pytest.fixture
def temp_dataset(sample_data):
    questions_data, meta_data = sample_data
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create directory structure
        data_dir = Path(tmp_dir) / "data"
        pdf_dir = Path(tmp_dir) / "pdfs"
        data_dir.mkdir()
        pdf_dir.mkdir()
        
        # Create sample PDF files
        (pdf_dir / "doc1.pdf").write_text("Sample PDF 1")
        (pdf_dir / "doc2.pdf").write_text("Sample PDF 2")
        
        # Write JSONL files
        questions_path = data_dir / "financebench_open_source.jsonl"
        meta_path = data_dir / "financebench_document_information.jsonl"
        
        with open(questions_path, "w") as f:
            for item in questions_data:
                f.write(json.dumps(item) + "\n")
                
        with open(meta_path, "w") as f:
            for item in meta_data:
                f.write(json.dumps(item) + "\n")
        
        yield tmp_dir


def test_init():
    dataset = FinanceBenchDataset("/dummy/path")
    assert dataset.data_path == Path("/dummy/path")
    assert dataset.questions_df is None
    assert dataset.meta_df is None
    assert dataset.pdf_dir is None


def test_load(temp_dataset):
    dataset = FinanceBenchDataset(temp_dataset)
    dataset.load()
    
    assert dataset.questions_df is not None
    assert dataset.meta_df is not None
    assert dataset.pdf_dir is not None
    assert len(dataset.questions_df) == 2
    assert len(dataset.meta_df) == 2


def test_get_document_paths(temp_dataset):
    dataset = FinanceBenchDataset(temp_dataset)
    dataset.load()
    
    paths = dataset.get_document_paths()
    assert len(paths) == 2
    assert all(path.suffix == ".pdf" for path in paths)


def test_get_questions(temp_dataset):
    dataset = FinanceBenchDataset(temp_dataset)
    dataset.load()
    
    questions = dataset.get_questions()
    assert len(questions) == 2
    assert questions[0].question == "What was the revenue in 2022?"
    assert questions[0].expected_answer == "The revenue in 2022 was $100M"


def test_get_metadata(temp_dataset):
    dataset = FinanceBenchDataset(temp_dataset)
    dataset.load()
    
    metadata = dataset.get_metadata()
    assert metadata["total_questions"] == 2
    assert metadata["total_documents"] == 2
    assert metadata["companies"] == ["TechCorp"]
    assert metadata["doc_types"] == ["10-K", "10-Q"]


def test_get_document_paths_no_dir():
    dataset = FinanceBenchDataset("/nonexistent/path")
    dataset.load = lambda: None  # Mock load method
    dataset.pdf_dir = Path("/nonexistent/path/pdfs")
    
    with pytest.raises(ValueError, match="PDF directory not found"):
        dataset.get_document_paths()


def test_get_questions_not_loaded():
    dataset = FinanceBenchDataset("/dummy/path")
    with pytest.raises(ValueError, match="Dataset not loaded"):
        dataset.get_questions()


def test_get_metadata_not_loaded():
    dataset = FinanceBenchDataset("/dummy/path")
    with pytest.raises(ValueError, match="Dataset not loaded"):
        dataset.get_metadata()