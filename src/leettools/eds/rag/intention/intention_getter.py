from abc import ABC, abstractmethod
from typing import Optional

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_section import StrategySection

DEFAULT_INTENTION = "default"


class AbstractIntentionGetter(ABC):

    @abstractmethod
    def get_intention(self, query: str) -> ChatQueryMetadata:
        """
        Get the intention of the query.
        """
        pass


def get_intention_getter_by_strategy(
    context: Context,
    user: User,
    intention_section: StrategySection,
    display_logger: Optional[EventLogger],
) -> AbstractIntentionGetter:
    """
    Get the intention getter based on the chat query options.
    """
    if (
        intention_section.strategy_name.lower() == "default"
        or intention_section.strategy_name.lower() == "true"
    ):
        from ._impl.intention_getter_dynamic import IntentionGetterDynamic

        return IntentionGetterDynamic(
            context=context,
            user=user,
            intention_section=intention_section,
            event_logger=display_logger,
        )
    else:
        raise exceptions.UnexpectedCaseException(
            f"Unknown intention strategy: {intention_section.strategy_name}"
        )
