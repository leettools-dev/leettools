import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .base_dataset import BaseDataset, QuestionItem


class FinanceBenchDataset(BaseDataset):
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.questions_df = None
        self.meta_df = None
        self.pdf_dir = None

    def load(self) -> None:
        # Load questions and metadata
        questions_path = self.data_path / "data/financebench_open_source.jsonl"
        meta_path = self.data_path / "data/financebench_document_information.jsonl"
        
        self.questions_df = pd.read_json(questions_path, lines=True)
        self.meta_df = pd.read_json(meta_path, lines=True)
        self.pdf_dir = self.data_path / "pdfs"

    def get_document_paths(self) -> List[Path]:
        if not self.pdf_dir.exists():
            raise ValueError(f"PDF directory not found: {self.pdf_dir}")
        
        return list(self.pdf_dir.glob("*.pdf"))

    def get_questions(self) -> List[QuestionItem]:
        if self.questions_df is None:
            raise ValueError("Dataset not loaded. Call load() first.")
        
        questions = []
        for _, row in self.questions_df.iterrows():
            question_item = QuestionItem(
                question=row["question"],
                expected_answer=row["answer"]
            )
            questions.append(question_item)
        
        return questions

    def get_metadata(self) -> Dict[str, Any]:
        if self.meta_df is None:
            raise ValueError("Dataset not loaded. Call load() first.")
        
        return {
            "total_questions": len(self.questions_df),
            "total_documents": len(self.meta_df),
            "companies": self.meta_df["company"].unique().tolist(),
            "doc_types": self.meta_df["doc_type"].unique().tolist()
        } 