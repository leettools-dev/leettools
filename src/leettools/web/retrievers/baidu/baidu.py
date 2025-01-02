import time
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.web import search_utils
from leettools.web.retrievers.retriever import AbstractRetriever
from leettools.web.schemas.search_result import SearchResult


class BaiduSearch(AbstractRetriever):
    """
    Baidu Search Retriever
    """

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        """
        Initializes the Baidu Search object
        """
        super().__init__(context, org, kb, user)
        self.logger.info(f"Installing Chrome Driver...")

        # Configure Chrome options to run in headless mode
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run Chrome in headless mode
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
        chrome_options.add_argument(
            "--disable-dev-shm-usage"
        )  # Overcome limited resource problems

        chrome_driver_path = "/usr/local/bin/chromedriver"
        self.driver = webdriver.Chrome(
            service=ChromeService(executable_path=chrome_driver_path),
            options=chrome_options,
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

        return self._retrieve(search_keywords, flow_options, display_logger)

    def _retrieve(
        self,
        query: str,
        flow_options: Dict[str, Any],
        display_logger: EventLogger,
    ) -> List[SearchResult]:

        days_limit, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=self.context.settings,
            display_logger=display_logger,
        )

        search_url = "https://www.baidu.com/s"

        gpc_param = (
            f"stf={int(time.time() - days_limit * 86400)},{int(time.time())}|stftype=2"
        )
        params = {
            "wd": query,
            "gpc": gpc_param,
        }
        search_url += "?" + "&".join(f"{k}={v}" for k, v in params.items())

        display_logger.info(f"Search url: \n{search_url}")
        self.driver.get(search_url)
        page_source = self.driver.page_source
        page_source.encode("utf-8")
        soup = BeautifulSoup(page_source, "html.parser")
        results = []

        actual_max_results = int(max_results / 0.6)
        while len(results) < actual_max_results:
            for item in soup.select(".result")[: actual_max_results - len(results)]:
                title_tag = item.select_one("h3 a")
                snippet_tag = item.select_one(".c-abstract")

                href = title_tag["href"] if title_tag else ""
                title = title_tag.get_text(strip=True) if title_tag else None
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else None

                results.append(SearchResult(href=href, title=title, snippet=snippet))

            # Check if there are more results by looking for the "next page" link
            next_page = soup.select_one("a.n")
            if next_page and len(results) < actual_max_results:
                next_page_url = next_page["href"]
                next_result_page = "https://www.baidu.com" + next_page_url
                display_logger.info(f"Next page: {next_result_page}")
                self.driver.get(next_result_page)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".result"))
                )
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
            else:
                break

        display_logger.info(f"Found {len(results)} results")
        return results
