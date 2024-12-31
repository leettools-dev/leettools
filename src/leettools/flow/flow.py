from abc import ABC, abstractmethod
from typing import ClassVar

from leettools.common.logging import EventLogger, logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import ChatQueryResultCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_component_type import FlowComponentType


class AbstractFlow(ABC, FlowComponent):

    FLOW_TYPE: ClassVar[str] = None
    ARTICLE_TYPE: ClassVar[str] = None
    COMPONENT_TYPE: ClassVar[FlowComponentType] = FlowComponentType.FLOW

    def __init__(self, context: Context):
        self.context = context
        self.settings = context.settings
        self.display_logger = logger()

    @abstractmethod
    def execute_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: EventLogger,
    ) -> ChatQueryResultCreate:
        """
        Execute the flow with the strategy specified in the given query.

        Args:
        -    org: Organization for the query
        -    kb: Knowledge base for the query
        -    user: User for the query
        -    chat_query_item: Chat query item for the query
        -    display_logger: Logger for the query

        Returns:
        -    The ChatQueryResultCreate for the query, which should be added
             to the chat history.
        """
        pass

    @classmethod
    def get_article_type(cls) -> str:
        """
        Get the output artcile type for the flow, such as
        * chat: chat message
        * article: multi-section article
        * search: search results
        * table: structured data

        We use string here so that new types can be added without changing the code.

        The result will be used by the front-end to determine the display.
        """
        return cls.ARTICLE_TYPE
