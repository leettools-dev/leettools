from typing import ClassVar, List, Type

from leettools.common.utils import config_utils
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.segment import SearchResultSegment
from leettools.core.strategy.schemas.strategy_conf import (
    SEARCH_OPTION_METRIC,
    SEARCH_OPTION_TOP_K,
)
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName
from leettools.eds.rag.search.searcher import create_searcher_for_kb
from leettools.eds.rag.search.searcher_type import SearcherType
from leettools.flow import flow_option_items
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep


class StepVectorSearch(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "vector_search"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return [flow_option_items.FOI_DOCSOURCE_UUID()]

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        query_metadata: ChatQueryMetadata,
        rewritten_query: str,
    ) -> List[SearchResultSegment]:
        context = exec_info.context
        settings = exec_info.settings
        display_logger = exec_info.display_logger
        org = exec_info.org
        kb = exec_info.kb
        user = exec_info.user
        query_options = exec_info.chat_query_options
        flow_options = query_options.flow_options
        query = exec_info.target_chat_query_item.query_content

        display_logger.info(f"[Status]Search in KB {kb.name} for related segments.")

        search_section = exec_info.strategy.strategy_sections.get(
            StrategySectionName.SEARCH, None
        )

        if search_section is None:
            display_logger.info(
                "Search section is not provided. Using default settings."
            )
            top_k = settings.DEFAULT_SEARCH_TOP_K
            metric_type = "COSINE"
            searcher_type = SearcherType.SIMPLE
        else:
            if search_section.strategy_name is None:
                searcher_type = SearcherType.SIMPLE
            else:
                if search_section.strategy_name == "simple":
                    searcher_type = SearcherType.SIMPLE
                elif search_section.strategy_name == "hybrid":
                    searcher_type = SearcherType.HYBRID
                else:
                    display_logger.warning(
                        f"Unknown searcher type: {search_section.strategy_name}. Using SIMPLE searcher."
                    )
                    searcher_type = SearcherType.SIMPLE

            if search_section.strategy_options is None:
                top_k = settings.DEFAULT_SEARCH_TOP_K
                metric_type = "COSINE"
            else:
                display_logger.debug(
                    f"Using search options: {search_section.strategy_options}"
                )
                top_k = config_utils.get_int_option_value(
                    options=search_section.strategy_options,
                    option_name=SEARCH_OPTION_TOP_K,
                    default_value=settings.DEFAULT_SEARCH_TOP_K,
                    display_logger=display_logger,
                )

                metric_type = config_utils.get_str_option_value(
                    options=search_section.strategy_options,
                    option_name=SEARCH_OPTION_METRIC,
                    default_value="COSINE",
                    display_logger=display_logger,
                )

        display_logger.debug(f"Using vector search type {searcher_type}.")
        searcher = create_searcher_for_kb(
            context=context,
            searcher_type=searcher_type,
            org=org,
            kb=kb,
        )
        search_params = {"metric_type": metric_type, "params": {"nprobe": top_k}}

        # the actual search is pretty expensive, so we skip it in test mode
        # may need a better way to test the full flow
        if context.is_test:
            top_ranked_result_segments = [
                SearchResultSegment(
                    segment_uuid="test-segment-uuid",
                    document_uuid="test-doc-id",
                    doc_uri="test-doc-uri",
                    docsink_uuid="test-docsink-uuid",
                    kb_id=kb.kb_id,
                    content="This is a test segment.",
                    search_score=1.0,
                    position_in_doc="1.1",
                    start_offset=0,
                    end_offset=0,
                )
            ]
            return top_ranked_result_segments

        filter_expr = None

        if False:
            # TODO next: we need a separate flow option for time range
            days_limit = config_utils.get_int_option_value(
                options=flow_options,
                option_name=flow_option.FLOW_OPTION_DAYS_LIMIT,
                default_value=None,
                display_logger=display_logger,
            )
            if days_limit is not None and days_limit != 0:
                end_ts = time_utils.cur_timestamp_in_ms()
                start_ts = end_ts - days_limit * 24 * 60 * 60 * 1000
                filter_expr = (
                    f"({TIMESTAMP_TAG_ATTR} >= {end_ts}) "
                    f"and ({TIMESTAMP_TAG_ATTR} <= {start_ts})"
                )

        display_logger.debug(
            f"The query flow options are: {query_options.flow_options}"
        )
        docsource_uuid = config_utils.get_str_option_value(
            options=flow_options,
            option_name=DocSource.FIELD_DOCSOURCE_UUID,
            default_value=None,
            display_logger=display_logger,
        )
        if docsource_uuid is not None:
            if filter_expr:
                filter_expr += (
                    f' and ({DocSource.FIELD_DOCSOURCE_UUID} == "{docsource_uuid}")'
                )
            else:
                filter_expr = f'{DocSource.FIELD_DOCSOURCE_UUID} == "{docsource_uuid}"'

        display_logger.debug(f"Using filter expression for vectdb: {filter_expr}")

        top_ranked_result_segments = searcher.execute_kb_search(
            org=org,
            kb=kb,
            user=user,
            query=query,
            rewritten_query=rewritten_query,
            top_k=top_k,
            search_params=search_params,
            query_meta=query_metadata,
            filter_expr=filter_expr,
        )
        display_logger.info(
            f"Found related segments by vectdb_search {len(top_ranked_result_segments)}:"
        )
        return top_ranked_result_segments
