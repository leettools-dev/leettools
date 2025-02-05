from typing import Any, Dict, List, Optional

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.eds.rag.search.filter import BaseCondition, Filter
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
        search_keywords: str,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[SearchResult]:

        if display_logger is None:
            display_logger = logger()
        context = self.context
        org = self.org
        kb = self.kb
        user = self.user

        from leettools.common.utils import config_utils

        display_logger.info(f"Searching with query: {search_keywords}...")

        days_limit, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=context.settings,
            display_logger=display_logger,
        )

        result_dict: Dict[str, str] = {}

        # we are reusing the local search code from the RAG searcher
        # this should the only place the web package uses the eds package
        from leettools.eds.rag.search.searcher import create_searcher_for_kb
        from leettools.eds.rag.search.searcher_type import SearcherType

        searcher = create_searcher_for_kb(
            context=context,
            searcher_type=SearcherType.HYBRID,
            org=org,
            kb=kb,
        )

        search_params = {
            "metric_type": "COSINE",
            "params": {
                "nprobe": max_results * 2,
            },
        }

        # TODO next: use the query time range to filter the search results
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
        if docsource_uuid is not None and docsource_uuid != "":
            docsink_store = context.get_repo_manager().get_docsink_store()
            docsource_store = context.get_repo_manager().get_docsource_store()
            try:
                docsource = docsource_store.get_docsource(org, kb, docsource_uuid)
                if docsource is None:
                    display_logger.debug(
                        f"LocalSearch: DocSource not found for docsource_uuid {docsource_uuid}"
                    )
                    return []
            except Exception as e:
                display_logger.debug(
                    f"LocalSearch: failed to lookup docsource {docsource_uuid}: {e}"
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

        display_logger.info(f"Using filter expression for local: {filter}")

        top_ranked_result_segments = searcher.execute_kb_search(
            org=org,
            kb=kb,
            user=user,
            query=search_keywords,
            rewritten_query=search_keywords,
            top_k=max_results * 2,
            search_params=search_params,
            query_meta=None,
            filter=filter,
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
