from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class QuestionItem:
    def __init__(self, question: str, expected_answer: str):
        self.question = question
        self.expected_answer = expected_answer

class BaseDataset(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load the dataset"""
        pass

    @abstractmethod
    def get_document_paths(self) -> List[Path]:
        """Get paths to all documents that need to be ingested"""
        pass

    @abstractmethod
    def get_questions(self) -> List[QuestionItem]:
        """Get all questions with their expected answers"""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Get dataset metadata"""
        pass 