from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.core.schemas.segment import Segment


class RerankResultItem(BaseModel):
    segment: Segment
    index: int
    relevance_score: float


class RerankResult(BaseModel):
    result_id: str
    results: List[RerankResultItem]
    metadata: Optional[Dict[str, Any]] = None
