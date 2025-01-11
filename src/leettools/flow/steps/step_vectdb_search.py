from typing import ClassVar, List, Type

from leettools.common import exceptions
from leettools.common.utils import config_utils
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.segment import SearchResultSegment, Segment
from leettools.core.strategy.schemas.strategy_conf import (
    SEARCH_OPTION_METRIC,
    SEARCH_OPTION_TOP_K,
)
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName
from leettools.eds.rag.search.filter import BaseCondition, Filter
from leettools.eds.rag.search.searcher import create_searcher_for_kb
from leettools.eds.rag.search.searcher_type import SearcherType
from leettools.flow import flow_option_items
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep
from leettools.web import search_utils


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
            document_store = context.get_repo_manager().get_document_store()
            documents = document_store.get_documents_for_kb(org, kb)
            if len(documents) == 0:
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
            else:
                display_logger.info("Found data in the test KB. Using real logic.")

        # TODO next: use the query time range to filter the search results
        days_limit, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=context.settings,
            display_logger=display_logger,
        )

        if days_limit != 0:
            start_ts, end_ts = config_utils.days_limit_to_timestamps(days_limit)
            filter = Filter(
                relation="and",
                conditions=[
                    BaseCondition(
                        field=Segment.FIELD_CREATED_TIMESTAMP_IN_MS,
                        operator=">=",
                        value=start_ts,
                    ),
                    BaseCondition(
                        field=Segment.FIELD_CREATED_TIMESTAMP_IN_MS,
                        operator="<=",
                        value=end_ts,
                    ),
                ],
            )
        else:
            filter = None

        docsource_uuid = config_utils.get_str_option_value(
            options=flow_options,
            option_name=DocSource.FIELD_DOCSOURCE_UUID,
            default_value=None,
            display_logger=display_logger,
        )
        if docsource_uuid is not None:
            docsink_store = context.get_repo_manager().get_docsink_store()
            docsource_store = context.get_repo_manager().get_docsource_store()
            try:
                docsource = docsource_store.get_docsource(org, kb, docsource_uuid)
                if docsource is None:
                    display_logger.debug(
                        f"DocSource not found for docsource_uuid: {docsource_uuid}"
                    )
                    return []
            except Exception as e:
                display_logger.debug(
                    f"DocSource not found for docsource_uuid: {docsource_uuid}: {e}"
                )
                return []
            docsinks = docsink_store.get_docsinks_for_docsource(org, kb, docsource)
            if len(docsinks) == 0:
                display_logger.warning(
                    f"No docsinks found for docsource {docsource_uuid}."
                )
            else:
                # TODO: this is a temporary solution to filter the search results by docsources
                # it may fail if the number of docsinks is too large
                docsink_uuids = [docsink.docsink_uuid for docsink in docsinks]
                if filter is not None:
                    filter = Filter(
                        relation="and",
                        conditions=[
                            filter,
                            BaseCondition(
                                field=DocSink.FIELD_DOCSINK_UUID,
                                operator="in",
                                value=docsink_uuids,
                            ),
                        ],
                    )
                else:
                    filter = BaseCondition(
                        field=DocSink.FIELD_DOCSINK_UUID,
                        operator="in",
                        value=docsink_uuids,
                    )

        display_logger.debug(f"Using filter expression for vectdb: {filter}")

        top_ranked_result_segments = searcher.execute_kb_search(
            org=org,
            kb=kb,
            user=user,
            query=query,
            rewritten_query=rewritten_query,
            top_k=top_k,
            search_params=search_params,
            query_meta=query_metadata,
            filter=filter,
        )
        display_logger.info(
            f"Found related segments by vectdb_search {len(top_ranked_result_segments)}."
        )
        return top_ranked_result_segments
