from typing import Any, Dict, List, Optional

from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment.FIELD_CREATED_TIMESTAMP_IN_MS
from leettools.core.schemas.user import User
from leettools.web import search_utils
from leettools.web.retrievers.retriever import AbstractRetriever
from leettools.web.schemas.search_result import SearchResult


class LocalSearch(AbstractRetriever):
    """
    Search Retriever for local KB
    """

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        super().__init__(context, org, kb, user)

    def retrieve_search_result(
        self,
        query: str,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[SearchResult]:

        from leettools.common.utils import config_utils

        display_logger.info(f"Searching with query: {query}...")

        days_limit, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=self.context.settings,
            display_logger=display_logger,
        )

        result_dict: Dict[str, str] = {}

        # we are reusing the local search code from the RAG searcher
        # this should the only place the web package uses the eds package
        from leettools.eds.rag.search.searcher import create_searcher_for_kb
        from leettools.eds.rag.search.searcher_type import SearcherType

        searcher = create_searcher_for_kb(
            context=self.context,
            searcher_type=SearcherType.HYBRID,
            org=self.org,
            kb=self.kb,
        )

        search_params = {
            "metric_type": "COSINE",
            "params": {
                "nprobe": max_results * 2,
            },
        }

        if days_limit != 0:
            start_ts, end_ts = config_utils.days_limit_to_timestamps(days_limit)
            filter_expr = (
                f"({Segment.FIELD_CREATED_TIMESTAMP_IN_MS} >= {start_ts}) "
                f"and ({Segment.FIELD_CREATED_TIMESTAMP_IN_MS} <= {end_ts})"
            )
        else:
            filter_expr = None

        docsource_uuid = config_utils.get_str_option_value(
            flow_options=flow_options,
            option_name=DocSource.FIELD_DOCSOURCE_UUID,
            default_value=None,
            display_logger=display_logger,
        )
        if docsource_uuid is not None:
            if filter_expr is not None:
                filter_expr += f" and "
            filter_expr = f'({DocSource.FIELD_DOCSOURCE_UUID} == "{docsource_uuid}")'

        display_logger.debug(f"Using filter expression for local: {filter_expr}")

        top_ranked_result_segments = searcher.execute_kb_search(
            org=self.org,
            kb=self.kb,
            user=self.user,
            query=query,
            rewritten_query=query,
            top_k=max_results * 2,
            search_params=search_params,
            query_meta=None,
            filter_expr=filter_expr,
        )

        for result_segement in top_ranked_result_segments:
            uri = result_segement.original_uri
            if uri is None:
                continue

            content = result_segement.content

            if uri in result_dict:
                result_dict[uri] += content
            else:
                result_dict[uri] = content
                if len(result_dict) >= max_results:
                    break

        result_list: List[SearchResult] = []

        for uri, content in result_dict.items():
            result_list.append(SearchResult(href=uri, snippet=content))

        return result_list
