from abc import ABC, abstractmethod
from typing import Optional

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.eds.rag.schemas.rewrite import Rewrite


class AbstractQueryRewriter(ABC):

    @abstractmethod
    def rewrite(
        self,
        org: Org,
        kb: KnowledgeBase,
        query: str,
        query_metadata: ChatQueryMetadata,
    ) -> Rewrite:
        """
        Rewrites the input query to a more detailed one.

        args:
        query: the input query
        query_metadata: the metadata of the query
        """
        pass


def get_query_rewriter_by_strategy(
    context: Context,
    user: User,
    rewrite_section: StrategySection,
    event_logger: Optional[EventLogger] = None,
) -> AbstractQueryRewriter:
    """
    Get the intention getter based on the strategy section.
    """
    strategy_name = rewrite_section.strategy_name
    if (
        strategy_name.lower() == "default"
        or strategy_name.lower() == "true"
        or strategy_name.lower() == "direct"
    ):
        from leettools.eds.rag.rewrite._impl.rewrite_direct_dynamic import (
            QueryRewriterDirectDynamic,
        )

        return QueryRewriterDirectDynamic(
            context=context,
            user=user,
            rewrite_section=rewrite_section,
            event_logger=event_logger,
        )
    elif strategy_name.lower() == "keywords":
        from leettools.eds.rag.rewrite._impl.rewrite_keywords_dynamic import (
            QueryRewriterKeywordsDynamic,
        )

        return QueryRewriterKeywordsDynamic(
            context=context,
            user=user,
            rewrite_section=rewrite_section,
            event_logger=event_logger,
        )
    else:
        raise exceptions.UnexpectedCaseException(
            f"Unknown query rewrite strategy: {strategy_name}"
        )
