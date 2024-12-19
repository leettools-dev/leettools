from abc import ABC, abstractmethod
from typing import Any, Dict, List

from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.eds.rag.schemas.rerank import RerankResult


class AbstractReranker(ABC):

    @abstractmethod
    def __init__(
        self,
        context: Context,
        user: User,
        rerank_section: StrategySection,
        display_logger: EventLogger,
    ):
        pass

    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[Segment],
        top_k: int,
        rerank_options: Dict[str, Any] = None,
    ) -> RerankResult:
        """
        Reranks the candidates based on the query.
        """
        pass


def create_reranker_by_strategy(
    context: Context,
    user: User,
    rerank_section: StrategySection,
    display_logger: EventLogger,
) -> AbstractReranker:

    from leettools.common.utils import factory_util

    settings = context.settings
    if rerank_section is None:
        strategy_name = settings.DEFAULT_RERANK_STRATEGY
    else:
        if rerank_section.strategy_name is None:
            strategy_name = settings.DEFAULT_RERANK_STRATEGY
        else:
            strategy_name = rerank_section.strategy_name

    # right now we have this naming convention for the strategy handler classes
    # basically the strategy section is the config to run the class
    # so the strategy handler classes cannot be arbitrary
    module_name = f"{__package__}._impl.reranker_{strategy_name.lower()}"

    return factory_util.create_object(
        module_name,
        AbstractReranker,
        context=context,
        user=user,
        rerank_section=rerank_section,
        display_logger=display_logger,
    )
