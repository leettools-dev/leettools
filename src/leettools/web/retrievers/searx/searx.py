import os
from typing import Any, Dict, List, Optional

import requests

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils.obj_utils import ENV_VAR_PREFIX
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.web import search_utils
from leettools.web.retrievers.retriever import AbstractRetriever
from leettools.web.schemas.search_result import SearchResult


class SearxSearch(AbstractRetriever):
    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        """
        Initializes the TavilySearch object
        Args:
            query:
        """
        super().__init__(context, org, kb, user)
        self.api_key = os.environ.get(
            f"{ENV_VAR_PREFIX}SEARX_URL", "https://baresearch.org/"
        )

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

        _, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=self.context.settings,
            display_logger=display_logger,
        )

        # TODO: convert flow_options to searx search parameters
        # Right now searx search does not work

        results = _search_searx_advanced(
            search_keywords,
            searx_url=self.api_key,
            categories=None,
            time_range=None,
            sites=None,
            display_logger=display_logger,
        )
        search_results = []
        for result in results:
            search_result = SearchResult(
                href=result["link"], title=result["title"], snippet=result["snippet"]
            )
            search_results.append(search_result)
        return search_results


def _search_searx_advanced(
    query: str,
    searx_url: str,
    max_results: int = 10,
    categories: Optional[List[str]] = None,
    time_range: Optional[str] = None,
    sites: Optional[List[str]] = None,
    display_logger: Optional[EventLogger] = None,
) -> List[Dict[str, str]]:
    """
    Advanced search using Searx with optional date range and target sites.
    Args:
    - query: The search query string.
    - searx_url: The base URL of the Searx instance.
    - categories: List of categories to search in (e.g., ['general', 'science']).
    - time_range: Date range for the search (e.g., 'day', 'week', 'month', 'year').
    - sites: List of specific sites to search within (e.g., ['example.com', 'another.com']).

    Return:
    - List of search results.
    """
    if display_logger is None:
        display_logger = logger()

    search_url = f"{searx_url}/search"
    params = {"q": query, "format": "json", "count": max_results}

    # Add categories
    if categories:
        params["categories"] = ",".join(categories)

    # Add date range
    if time_range:
        params["time_range"] = time_range

    # Add site restrictions
    if sites:
        site_query = " OR ".join([f"site:{site}" for site in sites])
        params["q"] = f"{query} {site_query}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        search_results = response.json()
        results = [
            {
                "title": result.get("title"),
                "link": result.get("url"),
                "snippet": result.get("content"),
            }
            for result in search_results.get("results", [])
        ]
        return results

    except requests.exceptions.HTTPError as e:
        display_logger.warning(
            f"HTTP error occurred: {e} - Response content: {response.text}"
        )

    return []


# Example usage
if __name__ == "__main__":

    context = ContextManager().get_context()
    ss = SearxSearch(context=context)
    query = "AI advancements"
    categories = ["general", "news"]
    time_range = "month"
    sites = ["example.com", "openai.com"]
    searx_instance = "https://searx.tiekoetter.com"
    results = _search_searx_advanced(
        query,
        searx_url=searx_instance,
        categories=categories,
        time_range=time_range,
        sites=sites,
    )

    for idx, result in enumerate(results, start=1):
        print(f"Result {idx}:")
        print(f"Title: {result['title']}")
        print(f"URL: {result['link']}")
        print(f"Snippet: {result['snippet']}\n")
