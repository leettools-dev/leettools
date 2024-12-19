from typing import Optional

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """
    Search result item from web retrievers.
    """

    href: str = Field(
        ...,
        description="The URL of the search result.",
    )
    title: Optional[str] = Field(
        None,
        description="The title of the search result.",
    )
    snippet: Optional[str] = Field(
        None,
        description="The snippet of the search result.",
    )
    document_uuid: Optional[str] = Field(
        None,
        description="The document_uuid of the search result if exists.",
    )
