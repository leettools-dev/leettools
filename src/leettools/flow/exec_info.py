from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from leettools.common.exceptions import UnexpectedCaseException
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_options import ChatQueryOptions
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy import Strategy
from leettools.eds.api_caller.api_caller_base import APICallerBase
from leettools.settings import SystemSettings


@dataclass
class ExecInfoBase:
    """
    This is the base class for ExecInfo, which contains the common runtime information
    that is not query specific.
    """

    context: Context
    org: Org
    kb: KnowledgeBase
    user: User
    display_logger: EventLogger

    def __post_init__(self):
        if self.display_logger is None:
            self.display_logger = logger()

    @property
    def settings(self) -> SystemSettings:
        return self.context.settings


@dataclass
class ExecInfo(ExecInfoBase):
    """
    The idea is to store the information about the query in a single memory storage,
    all the steps in a query execution flow will use this class to get the information
    about the query. Then for all the flow / subflow / steps, the input and output of
    each component will be explicit in their interface.
    """

    target_chat_query_item: ChatQueryItem

    query: Optional[str] = field(init=False)
    chat_query_options: Optional[ChatQueryOptions] = field(init=False)
    flow_type: Optional[str] = field(init=False)
    flow_options: Optional[Dict[str, Any]] = field(init=False)
    strategy: Optional[Strategy] = field(init=False)

    def __post_init__(self):
        # we have different places to determine the output language for the query
        # a tmp solution to store the output language here
        self.output_lang = None  # not specified, will be set if get_intention is called

        if self.target_chat_query_item is None:
            raise UnexpectedCaseException(
                "target_chat_query_item should not be None in exec_info."
            )
        strategy_store = self.context.get_strategy_store()

        self.query = self.target_chat_query_item.query_content
        self.chat_query_options = self.target_chat_query_item.get_chat_query_options()
        self.strategy = self.target_chat_query_item.get_strategy(
            strategy_store, self.display_logger
        )
        self.flow_type = self.target_chat_query_item.flow_type
        self.flow_options = self.chat_query_options.flow_options
        if self.flow_options is None:
            self.flow_options = {}

    def get_inference_caller(
        self, strategy: Optional[Strategy] = None
    ) -> APICallerBase:
        """
        Get the inference API caller based on the strategy. Using the strategy in the
        exec_info if not provided.
        """
        from leettools.core.strategy.schemas.strategy_section_name import (
            StrategySectionName,
        )
        from leettools.eds.rag.inference.inference import get_inference_by_strategy

        if strategy is None:
            strategy = self.strategy

        inference_section = strategy.strategy_sections.get(
            StrategySectionName.INFERENCE, None
        )

        if inference_section is None:
            raise UnexpectedCaseException("Inference section is missing from strategy.")

        api_caller: APICallerBase = get_inference_by_strategy(
            context=self.context,
            user=self.user,
            inference_section=inference_section,
            display_logger=self.display_logger,
        )

        return api_caller
