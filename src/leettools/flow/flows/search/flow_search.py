from typing import ClassVar, List, Optional, Type

from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import config_utils
from leettools.core.consts import flow_option
from leettools.core.consts.article_type import ArticleType
from leettools.core.consts.display_type import DisplayType
from leettools.core.consts.retriever_type import RetrieverType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import (
    ChatAnswerItemCreate,
    ChatQueryResultCreate,
)
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.pipeline.split import splitter
from leettools.flow import flow_option_items, steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.flow.utils import flow_utils


class FlowSearch(AbstractFlow):

    FLOW_TYPE: ClassVar[str] = FlowType.SEARCH.value
    ARTICLE_TYPE: ClassVar[str] = ArticleType.SEARCH.value
    COMPONENT_NAME: ClassVar[str] = FlowType.SEARCH.value

    @classmethod
    def short_description(cls) -> str:
        return "Search for top segements that match the query."

    @classmethod
    def full_description(cls) -> str:
        return """
Return top segements that match the query with links to the original documents.
- Perform the search with retriever: "local" for local KB, a search engine (e.g., Google)
  fetches top documents from the web. If no KB is specified, create an adhoc KB; 
  otherwise, save and process results in the KB.
- New web search results are processed through the document pipeline: conversion, 
  chunking, and indexing.
- Now the query is executed on the local KB using hybrid search, e.g., full text and 
  vector;
- The top matched segments, with the ranking score and the original document links;
- Right now SPLADE and Vector Cosine similarity are used in the hybried search.
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [steps.StepSearchToDocsource]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return AbstractFlow.direct_flow_option_items() + [
            flow_option_items.FOI_RETRIEVER(explicit=True),
            flow_option_items.FOI_DAYS_LIMIT(explicit=True),
            flow_option_items.FOI_TARGET_SITE(explicit=True),
            flow_option_items.FOI_SEARCH_MAX_RESULTS(),
            flow_option_items.FOI_SEARCH_LANGUAGE(),
            flow_option_items.FOI_SEARCH_MAX_ITERATION(),
            flow_option_items.FOI_SEARCH_RECURSIVE_SCRAPE(),
        ]

    def execute_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: Optional[EventLogger] = None,
    ) -> ChatQueryResultCreate:
        if display_logger is None:
            display_logger = self.display_logger

        # common setup
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

        # the agent flow starts here
        retriever_type = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_RETRIEVER_TYPE,
            default_value=exec_info.settings.WEB_RETRIEVER,
            display_logger=display_logger,
        )

        # the agent flow starts here
        if retriever_type == RetrieverType.LOCAL:
            # the run_vectdb_search function does not handle the days_limit option
            # and need a strategy section to run the search

            top_ranked_result_segments = steps.StepVectorSearch.run_step(
                exec_info=exec_info,
                query_metadata=None,
                rewritten_query=query,
            )
        else:
            # this is the initial search, similar to the "add search docsource" function
            docsource = steps.StepSearchToDocsource.run_step(exec_info=exec_info)
            flow_options[DocSource.FIELD_DOCSOURCE_UUID] = docsource.docsource_uuid

            top_ranked_result_segments = steps.StepVectorSearch.run_step(
                exec_info=exec_info,
                query_metadata=None,
                rewritten_query=query,
            )

        if top_ranked_result_segments == [] or top_ranked_result_segments is None:
            display_logger.debug(f"No segment found for query: {query}")
            return flow_utils.create_chat_result_for_empty_search(
                exec_info=exec_info, query_metadata=None
            )

        display_logger.debug(f"Found segments: {top_ranked_result_segments}")

        # create the chat answer items
        caic_list = []
        index = 0
        for result_segment in top_ranked_result_segments:
            index += 1
            # the heading actually has
            # page title / time stamp / titles for section path to the segment
            heading, content_display = splitter.separate_heading_from_content(
                result_segment.content
            )
            # we can do more beautification for the result display here
            if result_segment.content_display is None:
                result_segment.content_display = content_display
            caic = ChatAnswerItemCreate(
                chat_id=chat_query_item.chat_id,
                query_id=chat_query_item.query_id,
                answer_content=content_display,
                answer_plan=None,
                position_in_answer=str(index),
                answer_title=heading,
                answer_score=result_segment.search_score,
                answer_source_items={},
                position_layer=1,
                position_index=None,
                position_heading=None,
                display_type=DisplayType.SearchResultSegment,
                user_data=result_segment.model_dump(),
            )
            caic_list.append(caic)
        return ChatQueryResultCreate(
            chat_answer_item_create_list=caic_list,
            article_type=ArticleType.SEARCH.value,
        )
