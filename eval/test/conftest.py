import os
import tempfile
from pathlib import Path

import pytest


def pytest_configure(config):
    """Configure pytest"""
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup environment for all tests"""
    # Setup
    old_env = dict(os.environ)
    os.environ["TEST_MODE"] = "true"
    
    yield
    
    # Cleanup
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def sample_data():
    """Provide sample data for tests"""
    return {
        "questions": [
            {"question": "Test Q1", "answer": "Test A1"},
            {"question": "Test Q2", "answer": "Test A2"}
        ],
        "metadata": {
            "dataset": "test_dataset",
            "version": "1.0"
        }
    }


@pytest.fixture
def temp_test_dir():
    """Provide a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def create_test_file(path: Path, content: str) -> None:
    """Helper function to create test files"""
    path.write_text(content) 