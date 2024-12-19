from typing import ClassVar, List, Type

from leettools.common.logging.event_logger import EventLogger
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import (
    AnswerSource,
    ChatAnswerItemCreate,
    ChatQueryResultCreate,
    SourceItem,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import flow_option_items, steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType


class FlowDummy(AbstractFlow):

    ARTICLE_TYPE: ClassVar[str] = ArticleType.CHAT.value
    FLOW_TYPE: ClassVar[str] = FlowType.DUMMY.value
    COMPONENT_NAME: ClassVar[str] = FlowType.DUMMY.value

    @classmethod
    def short_description(cls) -> str:
        return "Dummy workflow used for testing."

    @classmethod
    def full_description(cls) -> str:
        return """
Dummy workflow used for testing.
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [steps.StepSearchToDocsource]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return AbstractFlow.direct_flow_option_items() + [
            flow_option_items.FOI_RETRIEVER(explicit=True, required=True),
            flow_option_items.FOI_DAYS_LIMIT(explicit=True, required=False),
            flow_option_items.FOI_TARGET_SITE(explicit=True, required=False),
            flow_option_items.FOI_OUTPUT_LANGUAGE(),
            flow_option_items.FOI_SEARCH_LANGUAGE(),
            flow_option_items.FOI_WORD_COUNT(),
            flow_option_items.FOI_STRICT_CONTEXT(),
            flow_option_items.FOI_PLANNING_MODEL(),
            flow_option_items.FOI_SUMMARY_MODEL(),
            flow_option_items.FOI_WRITING_MODEL(),
            flow_option_items.FOI_SEARCH_MAX_ITERATION(),
            flow_option_items.FOI_SEARCH_RECURSIVE_SCRAPE(),
        ]

    def execute_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: EventLogger,
    ) -> ChatQueryResultCreate:

        exec_info = ExecInfo(
            context=self.context,
            org=org,
            kb=kb,
            user=user,
            target_chat_query_item=chat_query_item,
            display_logger=display_logger,
        )

        query = exec_info.query
        chat_query_options = exec_info.chat_query_options
        flow_options = chat_query_options.flow_options
        if flow_options is None:
            flow_options = {}

        answer_source_items = {}
        answer_source_items["segment_id"] = SourceItem(
            index=1,
            source_segment_id="segment_id_11",
            answer_source=AnswerSource(
                source_document_uuid="",
                source_uri="",
                source_content="",
                score=1.0,
                position_in_doc="1.0",
                start_offset=0,
                end_offset=10,
                original_uri="",
            ),
        )
        chat_answer_item_create = ChatAnswerItemCreate(
            chat_id=chat_query_item.chat_id,
            query_id=chat_query_item.query_id,
            answer_content="This is a test report.",
            answer_plan=None,
            answer_score=1.0,
            answer_source_items=answer_source_items,
        )

        return ChatQueryResultCreate(
            chat_answer_item_create_list=[chat_answer_item_create]
        )
