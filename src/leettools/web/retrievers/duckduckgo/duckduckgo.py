from typing import Any, Dict, List, Optional

from duckduckgo_search import DDGS

from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.web import search_utils
from leettools.web.retrievers.retriever import AbstractRetriever
from leettools.web.schemas.search_result import SearchResult


class Duckduckgo(AbstractRetriever):
    """
    Duckduckgo API Retriever
    """

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        super().__init__(context, org, kb, user)
        self.ddg = DDGS()

    def retrieve_search_result(
        self,
        search_keywords: str,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[SearchResult]:
        if display_logger is None:
            display_logger = self.logger

        if flow_options is None:
            flow_options = {}

        display_logger.info(f"Searching with query {search_keywords}...")

        days_limit, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=self.context.settings,
            display_logger=display_logger,
        )

        ddgs_gen = self.ddg.text(
            search_keywords, region="wt-wt", max_results=max_results
        )

        """
        result = {
            "title": _normalize(title),
            "href": _normalize_url(href),
            "body": _normalize(body),
        }
        """

        search_results = []
        for result in ddgs_gen:
            search_result = SearchResult(
                href=result["href"], title=result["title"], snippet=result["body"]
            )
            search_results.append(search_result)
        return search_results
