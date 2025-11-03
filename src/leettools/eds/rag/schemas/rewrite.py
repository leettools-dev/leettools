from typing import Optional

from pydantic import BaseModel


class Rewrite(BaseModel):
    rewritten_question: str
    search_keywords: Optional[str] = None
