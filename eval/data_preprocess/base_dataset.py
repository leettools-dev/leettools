from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# @dataclass
# class AnswerSource:
#     ## source text are chunks from the source document
#     metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnswerSource:
    """Dynamic evidence information from source document"""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __getattr__(self, name: str) -> Any:
        """Allow accessing metadata keys as attributes"""
        if name in self.metadata:
            return self.metadata[name]
        raise AttributeError(f"'AnswerSource' has no attribute '{name}'")
    
    def keys(self):
        """Return metadata keys"""
        return self.metadata.keys()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from metadata with default"""
        return self.metadata.get(key, default)

@dataclass
class QuestionItem:
    """Question item with reference to source documents"""
    question: str
    expected_answer: str
    ## simple case that we have only one source document
    ## we can extend this to multiple source documents in the future
    source_document: str
    expected_sources: List[AnswerSource] = field(default_factory=list)  
    
    def __getattr__(self, name: str) -> Any:
        """Allow accessing metadata keys as attributes"""
        if name in self.metadata:
            return self.metadata[name]
        raise AttributeError(f"'QuestionItem' has no attribute '{name}'")

@dataclass
class BaseDataset(ABC):
    input_files: List[str] = field(default_factory=list)
    sample_data: List[QuestionItem] = field(default_factory=list)

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

