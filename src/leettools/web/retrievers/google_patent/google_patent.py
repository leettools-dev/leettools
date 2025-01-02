import urllib.parse
from typing import Any, Dict, List, Optional

from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils.file_utils import redact_api_key
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.web import search_utils
from leettools.web.retrievers.google.google import GoogleSearch
from leettools.web.retrievers.retriever import AbstractRetriever
from leettools.web.schemas.search_result import SearchResult


class GooglePatentSearch(GoogleSearch):
    """
    Google patent Search Retriever
    """

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        """
        Initializes the Google patent Search object
        """
        AbstractRetriever.__init__(self, context, org, kb, user)
        self.api_key = self._get_api_key()
        self.cx_key = self._get_cx_key(cx_name="GOOGLE_PATENT_CX_KEY")

    def retrieve_search_result(
        self,
        search_keywords: str,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[SearchResult]:
        """
        Useful for patent search queries using the Google API.
        Google API only allow return 10 results each time, so we need to
        set the start parameter to get more results.
        """
        if display_logger is None:
            display_logger = self.logger

        if flow_options is None:
            flow_options = {}

        return self._retrieve(search_keywords, flow_options, display_logger)

    def _retrieve(
        self,
        query: str,
        flow_options: Dict[str, Any],
        display_logger: EventLogger,
    ) -> List[SearchResult]:

        display_logger.info(f"Searching with query {query}...")

        days_limit, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=self.context.settings,
            display_logger=display_logger,
        )

        if days_limit == 0:
            date_restrict = ""
        else:
            date_restrict = f"&dateRestrict=d{days_limit}"

        iteration = 0
        start = 1
        search_results = []
        last_iteration_filled = True

        escaped_query = urllib.parse.quote(query)
        url_base = (
            f"https://www.googleapis.com/customsearch/v1?key={self.api_key}"
            f"&cx={self.cx_key}&q={escaped_query}"
        )
        redacted_url_base = (
            f"https://www.googleapis.com/customsearch/v1?key={redact_api_key(self.api_key)}"
            f"&cx={redact_api_key(self.cx_key)}&q={escaped_query}"
        )

        while len(search_results) < max_results and last_iteration_filled:
            iteration += 1

            url_paras = f"&safe=active" f"&start={start}" f"{date_restrict}"

            url = f"{url_base}{url_paras}"
            redacted_url = f"{redacted_url_base}{url_paras}"

            results = self._process_url(
                url=url,
                redacted_url=redacted_url,
                display_logger=display_logger,
            )
            if results is None:
                display_logger.warning(
                    f"[Iteration{iteration}] "
                    f"Failed Google API request for {redacted_url}."
                )
                return search_results

            if len(results) < 10:
                last_iteration_filled = False

            # Normalizing results to match the format of the other search APIs
            for result in results:
                href = result.get("link", None)
                if href is None or href == "":
                    self.logger.warning(f"Search result link missing: {result}")
                    continue

                self.logger.info(f"Search result link: {href}")
                search_result = SearchResult(
                    href=href,
                    title=result.get("title", None),
                    snippet=result.get("snippet", None),
                )
                search_results.append(search_result)
                if len(search_results) >= max_results:
                    break
            start += 10

        return search_results
