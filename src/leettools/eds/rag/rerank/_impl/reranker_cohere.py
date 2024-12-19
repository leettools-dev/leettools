import os
import uuid
from typing import Any, Dict, List

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.eds.api_caller.api_caller_base import APICallerBase
from leettools.eds.rag.rerank.reranker import AbstractReranker
from leettools.eds.rag.schemas.rerank import RerankResult, RerankResultItem

_script_dir = os.path.dirname(os.path.abspath(__file__))


class RerankerCohere(AbstractReranker, APICallerBase):

    def __init__(
        self,
        context: Context,
        user: User,
        rerank_section: StrategySection,
        display_logger: EventLogger,
    ):
        self.setup_with_strategy(
            context=context,
            user=user,
            strategy_section=rerank_section,
            script_dir=_script_dir,
            display_logger=display_logger,
        )

        # right now the rerank_options are not used in initialization
        # but we may use it in the future
        # rerank_options = rerank_section.strategy_options

    def rerank(
        self,
        query: str,
        documents: List[Segment],
        top_k: int,
        rerank_options: Dict[str, Any] = None,
    ) -> RerankResult:

        import cohere

        logger().info(f"Calling cohere reranker for query {query}")
        docs = [d.content for d in documents]

        model = self.model_name
        if rerank_options is not None:
            if rerank_options.get("model_name") is not None:
                model = rerank_options.get("model_name")

        response: cohere.RerankResponse = self.api_client.rerank(
            model=model,
            query=query,
            documents=docs,
            top_n=top_k,
        )

        results = []
        for i in range(top_k):
            if i >= len(response.results):
                break
            index = response.results[i].index
            results.append(
                RerankResultItem(
                    segment=documents[index],
                    index=index,
                    relevance_score=response.results[i].relevance_score,
                )
            )

        return RerankResult(
            result_id=str(uuid.uuid4()),
            results=results,
        )
