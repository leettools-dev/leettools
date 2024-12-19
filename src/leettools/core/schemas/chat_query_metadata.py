from typing import List, Optional

from pydantic import BaseModel, Field


class ChatQueryMetadata(BaseModel):
    intention: str = Field(..., description="The intention of the query.")
    language: Optional[str] = Field(None, description="The language of the query.")
    entities: Optional[List[str]] = Field(
        None, description="The entities found in the query."
    )
    keywords: Optional[List[str]] = Field(
        None, description="The keywords found in the query."
    )
