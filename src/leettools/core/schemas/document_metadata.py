from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    summary: Optional[str] = Field(None, description="The summary of the document")
    keywords: Optional[List[str]] = Field(
        [], description="Keywords found in the document"
    )
    links: Optional[List[str]] = Field([], description="Links found in the document")
    authors: Optional[List[str]] = Field([], description="Authors of the document")
    content_date: Optional[str] = Field(None, description="Date of the document")
    relevance_score: Optional[int] = Field(
        None, description="Relevance score to the topic of the Knowledge Base"
    )
