from typing import Any, Dict, List, Optional

from tavily import TavilyClient

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.user.user_settings_helper import get_value_from_settings
from leettools.web import search_utils
from leettools.web.retrievers.retriever import AbstractRetriever
from leettools.web.schemas.search_result import SearchResult


class TavilySearch(AbstractRetriever):
    """
    Tavily API Retriever
    """

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
        self.api_key = self._get_api_key(self.context)
        self.client = TavilyClient(self.api_key)

    def _get_api_key(self, context: Context) -> str:
        try:
            user = User.get_admin_user()
            user_settings = context.get_user_settings_store().get_settings_for_user(
                user
            )
            api_key = get_value_from_settings(
                context=context,
                user_settings=user_settings,
                default_env="TAVILY_API_KEY",
                first_key="TAVILY_API_KEY",
                second_key=None,
                allow_empty=False,
            )
        except:
            raise exceptions.UnexpectedCaseException(
                "Failed to get Tavily API key. Please set the TAVILY_API_KEY environment variable. "
                "You can get a key at https://app.tavily.com"
            )
        return api_key

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

        from leettools.common.utils import config_utils

        topic = config_utils.get_str_option_value(
            options=flow_options,
            option_name="tavily_search_topic",
            default_value="general",
            display_logger=display_logger,
        )

        _, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=self.context.settings,
            display_logger=display_logger,
        )

        # Search the query
        results = self.client.search(
            search_keywords,
            search_depth="basic",
            max_results=max_results,
            topic=topic,
        )

        sources = results.get("results", [])
        if not sources:
            raise exceptions.UnexpectedCaseException(
                "No results found with Tavily API search."
            )

        search_results = [
            SearchResult(href=obj["url"], snippet=obj["content"]) for obj in sources
        ]
        return search_results
