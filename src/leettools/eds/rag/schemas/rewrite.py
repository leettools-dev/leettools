from typing import List, Optional

from pydantic import BaseModel


class Rewrite(BaseModel):

    rewritten_question: str
    rewritten_keywords: Optional[List[str]] = None
