import uuid
from typing import Any, Dict, List

from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.eds.rag.rerank.reranker import AbstractReranker
from leettools.eds.rag.schemas.rerank import RerankResult, RerankResultItem


class RerankerDummy(AbstractReranker):

    def __init__(
        self,
        context: Context,
        user: User,
        rerank_section: StrategySection,
        display_logger: EventLogger,
    ):
        pass

    def rerank(
        self,
        query: str,
        documents: List[Segment],
        top_k: int,
        rerank_options: Dict[str, Any] = None,
    ) -> RerankResult:
        results = []
        for i in range(top_k):
            if i >= len(documents):
                break
            results.append(
                RerankResultItem(
                    segment=documents[i],
                    index=i,
                    relevance_score=1.0 - i / top_k,  # dummy relevance score
                )
            )

        return RerankResult(
            result_id=str(uuid.uuid4()),
            results=results,
        )
