from typing import Any, Dict, List, Optional

import requests

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.web import search_utils
from leettools.web.retrievers.retriever import AbstractRetriever
from leettools.web.schemas.search_result import SearchResult


class BingSearch(AbstractRetriever):
    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        super().__init__(context, org, kb, user)
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"
        self.bing_search_api_key = context.settings.BING_SEARCH_API_KEY

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

        days_limit, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=self.context.settings,
            display_logger=display_logger,
        )

        # Your Bing Search API key
        headers = {"Ocp-Apim-Subscription-Key": self.bing_search_api_key}

        # Construct the query parameters
        actual_max_results = int(max_results / 0.6)
        params = {
            "q": search_keywords,
            "count": actual_max_results,
            "mkt": "zh-CN",
            "freshness": (
                "Day" if days_limit == 1 else "Week" if days_limit <= 7 else "Month"
            ),
            "responseFilter": "Webpages",
        }

        response = requests.get(self.base_url, headers=headers, params=params)

        display_logger.info(f"Bing Search API request URL: {response.url}")

        response.raise_for_status()
        search_results = response.json()
        results = []
        if "webPages" in search_results and "value" in search_results["webPages"]:
            for item in search_results["webPages"]["value"]:
                result = SearchResult(
                    href=item["url"],
                    title=item.get("name"),
                    snippet=item.get("snippet"),
                )
                results.append(result)

        return results
