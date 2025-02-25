import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .base_dataset import AnswerSource, BaseDataset, QuestionItem
from .config import DEFAULT_FINANCEBENCH_PATH


class FinanceBenchDataset(BaseDataset):
    def __init__(self, data_path: str | Path = DEFAULT_FINANCEBENCH_PATH):
        super().__init__()
        self.data_path = Path(data_path)
        
        # Initialize paths
        self.questions_path = self.data_path / "data" / "financebench_open_source.jsonl"
        self.meta_path = self.data_path / "data" / "financebench_document_information.jsonl"
        self.pdf_dir = self.data_path / "pdfs"

        # Validate paths before loading
        self._validate_paths()
        
        # Load data
        self._load_data()

    def _validate_paths(self):
        """Validate that all required paths exist"""
        if not self.questions_path.exists():
            raise FileNotFoundError(f"Questions file not found at {self.questions_path}")
        if not self.meta_path.exists():
            raise FileNotFoundError(f"Metadata file not found at {self.meta_path}")
        if not self.pdf_dir.exists():
            raise FileNotFoundError(f"PDF directory not found at {self.pdf_dir}")

    def _load_data(self):
        """Load data from files"""
        self.questions_df = pd.read_json(self.questions_path, lines=True)
        self.meta_df = pd.read_json(self.meta_path, lines=True)

    def _convert_evidence(self, evidence_list: List[Dict[str, Any]]) -> List[AnswerSource]:
        """Convert JSON evidence list to AnswerSource objects dynamically"""
        if not evidence_list:
            return []

        return [AnswerSource(metadata=ev) for ev in evidence_list]

    def get_document_paths(self) -> List[Path]:
        if not self.pdf_dir.exists():
            raise ValueError(f"PDF directory not found: {self.pdf_dir}")

        paths = list(self.pdf_dir.glob("*.pdf"))
        print(f"\nFound {len(paths)} PDF documents")

        # # Get the document names from the questions DataFrame
        # document_names = set(self.questions_df['doc_name'].unique())

        # # Filter PDF files based on document names
        # pdf_files = [
        #     pdf for pdf in paths
        #     if pdf.stem in document_names  # Check if the PDF name (without extension) is in document names
        # ]

        return self.questions_df["doc_name"].apply(
            lambda x: self.pdf_dir / f"{x}.pdf"
        ).tolist()

    def get_questions(self) -> List[QuestionItem]:
        if self.questions_df is None:
            raise ValueError("Dataset not loaded. Call load() first.")
        
        questions = []
        for _, row in self.questions_df.iterrows():
            evidence_list = row.get('evidence', [])
            expected_sources = self._convert_evidence(evidence_list)

            ## May also include "question_type", "question_reasoning", "justification" in the future
            question_item = QuestionItem(
                question=row["question"],
                expected_answer=row["answer"],
                source_document=row["doc_name"],
                expected_sources=[{"source_text": ev.metadata["evidence_text"]} for ev in expected_sources],
                # Sample sources: length: 1, keys: dict_keys(['evidence_text', 'doc_name', 'evidence_page_num', 'evidence_text_full_page'])
                # Firstly just use evidence_text as the source text
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