from typing import Any, Dict, List, Optional

from firecrawl import FirecrawlApp

from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import config_utils
from leettools.context_manager import Context
from leettools.core.consts import flow_option
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.user.user_settings_helper import get_value_from_settings
from leettools.web.retrievers.retriever import AbstractRetriever
from leettools.web.schemas.search_result import SearchResult


class FirecrawlSearch(AbstractRetriever):
    """
    Firecrawl Search Retriever
    """

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        """
        Initializes the Google Search object
        Args:
            query:
        """
        super().__init__(context, org, kb, user)
        self.api_key = self._get_api_key()
        self.api_url = self._get_api_url()
        self.app = FirecrawlApp(api_key=self.api_key, api_url=self.api_url)

    def retrieve_search_result(
        self,
        search_keywords: str,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[SearchResult]:
        """
        An example of the search result from Firecrawl:
        {
            'success': True,
            'data': [
                {
                    'url': 'https://www.firecrawl.dev/',
                    'title': 'Firecrawl',
                    'description': "Turn websites into LLM-ready data. Power your AI apps with clean data crawled from any website. It's also open-source. Start for free (500 credits)"
                },
                {
                    'url': 'https://github.com/mendableai/firecrawl',
                    'title': 'mendableai/firecrawl: Turn entire websites into LLM-ready ... - GitHub',
                    'description': 'Firecrawl is an API service that takes a URL, crawls it, and converts it into clean markdown or structured data. We crawl all accessible subpages and give you ...'
                },
                {
                    'url': 'https://python.langchain.com/docs/integrations/document_loaders/firecrawl/',
                    'title': 'FireCrawl | 🦜️   LangChain',
                    'description': 'FireCrawl crawls and convert any website into LLM-ready data. It crawls all accessible subpages and give you clean markdown and metadata for each.'
                },
                {
                    'url': 'https://www.ycombinator.com/companies/firecrawl',
                    'title': 'Firecrawl: The easiest way to extract AI ready data from the web',
                    'description': 'Firecrawl is the easiest way to extract data from the web. Developers use us to reliably convert URLs into LLM-ready markdown or structured data with a single ...'
                }
            ]
        }
        """
        if display_logger is None:
            display_logger = self.logger

        limit = config_utils.get_int_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_SEARCH_MAX_RESULTS,
            default_value=10,
            display_logger=display_logger,
        )
        search_results = []
        try:
            search_result_dict: Dict[str, Any] = self.app.search(
                query=search_keywords, params={"limit": limit}
            )
            if search_result_dict.get("success", False):
                result_list = search_result_dict.get("data", [])
                if isinstance(result_list, list):
                    for data in result_list:
                        if not isinstance(data, dict):
                            self.logger.warning(
                                f"The search result from Firecrawl is not a dictionary: {data}"
                            )
                            continue
                        url = data.get("url", None)
                        if url:
                            search_result = SearchResult(
                                href=url,
                                title=data.get("title", ""),
                                snippet=data.get("description", ""),
                            )
                            search_results.append(search_result)
                        else:
                            self.logger.warning(
                                f"The search result from Firecrawl does not have a URL: {data}"
                            )
                else:
                    self.logger.warning(
                        f"The search result from Firecrawl is not a list: {result_list}"
                    )
        except Exception as e:
            self.logger.error(f"Failed to retrieve search results from Firecrawl: {e}")
        return search_results

    def _get_api_key(self) -> str:
        try:
            if self.user is not None:
                user = User.get_admin_user()
            else:
                user = self.user

            user_settings = (
                self.context.get_user_settings_store().get_settings_for_user(user)
            )
            # the get_value_from_settings will fall back to admin_user settings
            # if the user settings has no keys
            api_key = get_value_from_settings(
                context=self.context,
                user_settings=user_settings,
                default_env="FIRECRAWL_API_KEY",
                first_key="FIRECRAWL_API_KEY",
                second_key=None,
                allow_empty=False,
            )
        except Exception as e:
            self.logger.debug(
                "Failed to get FireCrawl API key. Maybe using a proxy, set the dummp key "
                "instead. If possible, please set the EDS_FIRECRAWL_API_KEY environment variable. "
                f"{e}"
            )
            raise e
        return api_key

    def _get_api_url(self) -> str:
        try:
            if self.user is not None:
                user = User.get_admin_user()
            else:
                user = self.user

            user_settings = (
                self.context.get_user_settings_store().get_settings_for_user(user)
            )
            # the get_value_from_settings will fall back to admin_user settings
            # if the user settings has no keys
            api_url = get_value_from_settings(
                context=self.context,
                user_settings=user_settings,
                default_env="FIRECRAWL_API_URL",
                first_key="FIRECRAWL_API_URL",
                second_key=None,
                allow_empty=True,
            )
            if api_url is None or api_url == "":
                api_url = "https://api.firecrawl.dev"
        except Exception as e:
            self.logger.debug(
                "Failed to get FireCrawl API URL. Using the default URL. "
            )
            api_url = "https://api.firecrawl.dev"
        return api_url
