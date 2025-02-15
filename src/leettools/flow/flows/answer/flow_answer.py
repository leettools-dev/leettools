from typing import ClassVar, List, Type

import leettools.flow.utils.citation_utils
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import config_utils
from leettools.core.consts import flow_option
from leettools.core.consts.article_type import ArticleType
from leettools.core.consts.display_type import DisplayType
from leettools.core.consts.retriever_type import RetrieverType, is_search_engine
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.chat_query_result import (
    ChatAnswerItemCreate,
    ChatQueryResultCreate,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.rag.intention.intention_getter import DEFAULT_INTENTION
from leettools.flow import flow_option_items, steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.flow.utils import flow_utils


class FlowAnswer(AbstractFlow):

    FLOW_TYPE: ClassVar[str] = FlowType.ANSWER.value
    ARTICLE_TYPE: ClassVar[str] = ArticleType.CHAT.value
    COMPONENT_NAME: ClassVar[str] = FlowType.ANSWER.value

    @classmethod
    def short_description(cls) -> str:
        return "Answer the query directly with source references."

    @classmethod
    def full_description(cls) -> str:
        return """
Search the web or local KB with the query and answer with source references:
- Perform the search with retriever: "local" for local KB, a search engine
  (e.g., google) fetches top documents from the web. If no KB is specified, 
  create an adhoc KB; otherwise, save and process results in the KB.
- New web search results are processed by the document pipeline: conversion,
  chunking, and indexing.
- Retrieve top matching segments from the KB based on the query.
- Concatenate the segments to create context for the query.
- Use the context to answer with source references via an LLM API call.
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [
            steps.StepSearchToDocsource,
            steps.StepIntention,
            steps.StepQueryRewrite,
            steps.StepVectorSearch,
            steps.StepInference,
            steps.StepRerank,
            steps.StepExtendContext,
        ]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return AbstractFlow.direct_flow_option_items() + [
            flow_option_items.FOI_RETRIEVER(explicit=True),
            flow_option_items.FOI_REFERENCE_STYLE(),
            flow_option_items.FOI_REFERENCE_STYLE(),
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
        flow_options = exec_info.flow_options

        retriever_type = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_RETRIEVER_TYPE,
            default_value=exec_info.settings.WEB_RETRIEVER,
            display_logger=display_logger,
        )

        reference_style = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_REFERENCE_STYLE,
            default_value=flow_option_items.FOI_REFERENCE_STYLE().default_value,
            display_logger=display_logger,
        )

        # flow starts there
        if is_search_engine(retriever_type):
            # query the web first, after this function, the search results
            # are processed and stored in the KB
            # TODO: make this function async
            docsource = steps.StepSearchToDocsource.run_step(exec_info=exec_info)
            # we will answer using the whole KB
            # right now filter by docsource cannot include re-used docsinks
            # flow_options[DOCSOURCE_UUID_ATTR] = docsource.docsource_uuid

        if retriever_type == RetrieverType.LOCAL.value:
            query_metadata = steps.StepIntention.run_step(exec_info=exec_info)

            rewritten_query = steps.StepQueryRewrite.run_step(
                exec_info=exec_info,
                query=query,
                query_metadata=query_metadata,
            )
        else:
            query_metadata = ChatQueryMetadata(intention=DEFAULT_INTENTION)
            rewritten_query = query

        top_ranked_result_segments = steps.StepVectorSearch.run_step(
            exec_info=exec_info,
            query_metadata=query_metadata,
            rewritten_query=rewritten_query,
        )
        if len(top_ranked_result_segments) == 0:
            return flow_utils.create_chat_result_for_empty_search(
                exec_info=exec_info,
                query_metadata=query_metadata,
            )

        reranked_result = steps.StepRerank.run_step(
            exec_info=exec_info,
            top_ranked_result_segments=top_ranked_result_segments,
        )

        extended_context, context_token_count, source_items = (
            steps.StepExtendContext.run_step(
                exec_info=exec_info,
                reranked_result=reranked_result,
                accumulated_source_items={},
            )
        )

        display_logger.debug(
            f"The context text length is: {len(extended_context)}. "
            f"The token count is: {context_token_count}. "
            f"The number of new source items is: {len(source_items)}. "
        )

        from openai.resources.chat.completions import ChatCompletion

        completion: ChatCompletion = steps.StepInference.run_step(
            exec_info=exec_info,
            query_metadata=query_metadata,
            rewritten_query=rewritten_query,
            extended_context=extended_context,
        )

        display_logger.info(f"Query finished successfully: {query}.")

        result_content = completion.choices[0].message.content

        answer_content, reorder_cited_source_items = (
            flow_utils.inference_result_to_answer(
                result_content=result_content,
                source_items=source_items,
                reference_style=reference_style,
                display_logger=display_logger,
            )
        )

        caic_list = []
        caic_answer = ChatAnswerItemCreate(
            chat_id=chat_query_item.chat_id,
            query_id=chat_query_item.query_id,
            answer_content=answer_content,
            position_in_answer="1",
            answer_plan=None,
            answer_score=1.0,
            answer_source_items=reorder_cited_source_items,
        )
        caic_list.append(caic_answer)

        reference_section_str = (
            leettools.flow.utils.citation_utils.create_reference_section(
                exec_info, reorder_cited_source_items
            )
        )

        if reference_section_str != "":
            caic_references = ChatAnswerItemCreate(
                chat_id=chat_query_item.chat_id,
                query_id=chat_query_item.query_id,
                answer_content=reference_section_str,
                answer_plan=None,
                answer_title="References",
                position_in_answer="2",
                answer_score=1.0,
                display_type=DisplayType.REFERENCES,
                user_data=None,
            )
            caic_list.append(caic_references)

        return ChatQueryResultCreate(
            chat_answer_item_create_list=caic_list,
            global_answer_source_items=reorder_cited_source_items,
            article_type=ArticleType.CHAT.value,
        )
