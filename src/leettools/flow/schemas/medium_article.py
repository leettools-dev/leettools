from typing import List, Optional

from pydantic import BaseModel


class MediumArticle(BaseModel):
    id: str
    title: str
    summary: str
    author_id: str
    claps: int
    responses: int
    body: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    twitter_connects: Optional[List[str]] = None
    read_length: Optional[int] = None
