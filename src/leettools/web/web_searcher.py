from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Type

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import config_utils, file_utils
from leettools.context_manager import Context
from leettools.core.consts import flow_option
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import flow_option_items
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_component_type import FlowComponentType
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.web.retrievers.retriever import create_retriever
from leettools.web.schemas.scrape_result import ScrapeResult
from leettools.web.schemas.search_result import SearchResult
from leettools.web.web_scraper import WebScraper


def _get_docsink_create_from_saved_files(
    kb: KnowledgeBase,
    docsource: DocSource,
    scrape_results: List[ScrapeResult],
) -> List[DocSinkCreate]:
    """
    Process the scraper results and create a list of DocSinkCreate objects.

    Args:
        kb (KnowledgeBase): The KnowledgeBase object.
        docsource (DocSource): The DocSource object.
        saved_files (List[ScrapeResult]): The list of ScrapeResult objects.

    Returns:
        List[DocSinkCreate]: The list of DocSinkCreate objects.
    """

    docsink_create_list = []

    for result in scrape_results:
        original_url = result.url
        file_path = result.file_path
        doc_hash, doc_size = file_utils.file_hash_and_size(Path(file_path))
        docsink_create = DocSinkCreate(
            docsource=docsource,
            original_doc_uri=original_url,
            raw_doc_uri=file_path,
            raw_doc_hash=doc_hash,
            size=doc_size,
        )
        docsink_create_list.append(docsink_create)
    return docsink_create_list


class WebSearcher(FlowComponent):
    """
    Right now this class is not thread-safe. Do not reuse in different threads.

    TOOD: will turn this into a service in the future.
    """

    # TODO: how to prevent the external steps to use the same component name?
    COMPONENT_TYPE: ClassVar[FlowComponentType] = FlowComponentType.STEP
    COMPONENT_NAME: ClassVar[str] = "web_searcher"

    @classmethod
    def short_description(cls) -> str:
        return "The web search component."

    @classmethod
    def full_description(cls) -> str:
        return """Given a query, search the web, scrape the results, and save them to 
local storage.
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        # TODO: different retriever types have different options
        return [
            flow_option_items.FOI_RETRIEVER(),
            flow_option_items.FOI_DAYS_LIMIT(),
            flow_option_items.FOI_SEARCH_MAX_RESULTS(),
            flow_option_items.FOI_TARGET_SITE(),
            flow_option_items.FOI_IMAGE_SEARCH(),
            flow_option_items.FOI_SEARCH_EXCLUDED_SITES(),
            flow_option_items.FOI_SEARCH_MAX_ITERATION(),
        ]

    def __init__(self, context: Context):

        self.context = context
        self.settings = context.settings
        repo_manager = context.get_repo_manager()
        self.docsource_store = repo_manager.get_docsource_store()
        self.docsink_store = repo_manager.get_docsink_store()

        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()

        self.output_root = f"{self.settings.DATA_ROOT}/websearch"
        # visited_urls stores the url to path mapping
        self.visited_urls: Dict[str, str] = {}

        self.logger = logger()  # default logger
        self.display_logger = self.logger  # logs that we want to show on UI

    def _get_new_urls(self, url_list: List[str]) -> list[str]:
        """
        Gets the new urls from the given url set.
        Args:
        - url_list (list[str]): The url list to check

        Returns:
        - list[str]: The new urls from the given url set
        """

        new_urls = []
        for url in url_list:
            if url not in self.visited_urls:
                new_urls.append(url)
                self.display_logger.info(f"✅ Added url to scraper: {url}")

        return new_urls

    def create_docsinks_by_search_and_scrape(
        self,
        context: Context,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        search_keywords: str,
        docsource: DocSource,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[DocSinkCreate]:
        """
        Using the URI from the docsource to get the spec and performa the search. The
        result will be scraped and saved to the output directory. No summary or relevance
        checking is done here.

        Args:
        - context (Context): the Context object.
        - org (Org): The organization object.
        - kb (KnowledgeBase): The KnowledgeBase object.
        - user (User): The user object.
        - search_keywords (str): The search keywords string.
        - docsource (DocSource): The document source.
        - flow_options (Optional[Dict[str, Any]]): The flow options.
        - display_logger (Optional[EventLogger]): The display logger.

        Returns:
        - DocSinkCreate: a list of DocSinkCreate objects.
        """
        if display_logger is None:
            display_logger = logger()

        if flow_options is None:
            flow_options = {}

        retrieve_type = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_RETRIEVER_TYPE,
            default_value=context.settings.WEB_RETRIEVER,
            display_logger=display_logger,
        )
        retriever = create_retriever(
            retriever_type=retrieve_type,
            context=context,
            org=org,
            kb=kb,
            user=user,
        )

        search_results = retriever.retrieve_search_result(
            search_keywords=search_keywords,
            flow_options=flow_options,
            display_logger=display_logger,
        )

        if len(search_results) == 0:
            display_logger.info(f"No search results found for query {search_keywords}.")
            return []

        new_search_urls = self._get_new_urls(
            [search_result.href for search_result in search_results]
        )

        docsink_create_list = self.scrape_urls_to_docsinks(
            query=search_keywords,
            org=org,
            kb=kb,
            docsource=docsource,
            links=new_search_urls,
            display_logger=display_logger,
        )

        display_logger.info(f"Found {len(docsink_create_list)} docsinks to be created.")

        return docsink_create_list

    def scrape_urls_to_docsinks(
        self,
        query: str,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
        links: List[str],
        display_logger: Optional[EventLogger] = None,
    ) -> List[DocSinkCreate]:
        """
        Scrape the URLs and create documents for an existing docsource.

        Args:
        - query (str): The query string.
        - org (Org): The organization object.
        - kb (KnowledgeBase): The KnowledgeBase object.
        - docsource (DocSource): The DocSource object.
        - links (List[str]): The list of URLs to scrape.
        - display_logger (Optional[EventLogger]): The display logger.

        Returns:
        - List[DocSinkCreate]: The documents created
        """
        if display_logger is None:
            display_logger = self.display_logger

        scraper = WebScraper(context=self.context, display_logger=display_logger)
        scrape_results = scraper.scrape_urls_to_file(links)

        display_logger.info(f"Scraped {len(scrape_results)} results for {query}")

        docsink_create_list = _get_docsink_create_from_saved_files(
            kb=kb, docsource=docsource, scrape_results=scrape_results
        )
        return docsink_create_list

    def simple_search(
        self,
        context: Context,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        search_keywords: str,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[SearchResult]:
        """
        Perform a simple search and return the search results.
        Args:
        - context (Context): the Context object.
        - org (Org): The organization object.
        - kb (KnowledgeBase): The KnowledgeBase object.
        - user (User): The user object.
        - search_keywords (str): The search keywords string.
        - flow_options (Optional[Dict[str, Any]]): The flow options.
        - display_logger (Optional[EventLogger]): The display logger.
        """
        if display_logger is None:
            display_logger = logger()

        if flow_options is None:
            flow_options = {}

        retrieve_type = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_RETRIEVER_TYPE,
            default_value=context.settings.WEB_RETRIEVER,
            display_logger=display_logger,
        )
        retriever = create_retriever(
            retriever_type=retrieve_type,
            context=context,
            org=org,
            kb=kb,
            user=user,
        )

        search_results = retriever.retrieve_search_result(
            search_keywords=search_keywords,
            flow_options=flow_options,
            display_logger=display_logger,
        )

        if len(search_results) == 0:
            display_logger.info(f"No search results found for query {search_keywords}.")
            return []

        return search_results
