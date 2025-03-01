import os
import traceback
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
from typing import List, Optional

import requests

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import url_utils
from leettools.context_manager import Context
from leettools.core.consts.return_code import ReturnCode
from leettools.web.schemas.scrape_result import ScrapeResult
from leettools.web.scrapers.scraper import get_scraper


class WebScraper:
    """
    Scraper class to save data from the links to local files. This class should be
    the entry point for all the scraping tasks. It uses the appropriate scraper based
    on the URL and saves the data to the local file system.

    For exmple:
    - For HTML files, it uses BeautifulSoup to remove the ads and scripts and save the content.
    - For PDF files, it saves the raw file.
    - For Arxiv papers, it saves the abstract and the content.
    """

    def __init__(
        self,
        context: Context,
        user_agent: str = None,
        scraper_type: str = None,
        display_logger: EventLogger = None,
    ):
        self.context = context
        self.settings = context.settings

        self.session = requests.Session()
        if user_agent is not None:
            self.user_agent = user_agent
        else:
            self.user_agent = url_utils.DEFAULT_USER_AGENT

        self.session.headers.update({"User-Agent": self.user_agent})
        if scraper_type is None or scraper_type == "":
            self.scraper_type = self.settings.DEFAULT_SCRAPER
        else:
            self.scraper_type = scraper_type
        self.output_root = f"{self.settings.DATA_ROOT}/websearch"

        if display_logger is not None:
            self.display_logger = display_logger
        else:
            self.display_logger = logger()

    def scrape_urls_to_file(self, urls: List[str]) -> List[ScrapeResult]:
        """
        Scrape the list of URLs and extract the content from them.

        Args:
        - urls: A list of strings representing the URLs to extract content from

        Returns:
        - A list of ScrapeResult objects
        """
        partial_extract = partial(self._save_data_from_link)
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = executor.map(partial_extract, urls)
        res = [result for result in results if result.file_path is not None]
        return res

    def scrape_url_to_content(self, url: str) -> Optional[str]:
        """
        Scrape the content from the URL and return the content as a string.
        Args:
        - url (str): The URL of the link to extract data from.
        Returns:
        - str: The content extracted from the URL.
        """
        display_logger = self.display_logger
        try:
            scraper = get_scraper(
                url=url,
                session=self.session,
                default_type=self.scraper_type,
                display_logger=self.display_logger,
            )
            return scraper.scrape_content_to_str(url)
        except Exception as e:
            trace = traceback.format_exc()
            display_logger.debug(
                f"Error scraping (failure): {url} to content, exception: {e}"
            )
            display_logger.debug(f"Detailed error: {trace}")
            return None

    def _get_dir_for_url(self, url: str) -> str:
        tld = url_utils.get_first_level_domain_from_url(url)
        target_dir = os.path.join(self.output_root, tld)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        return target_dir

    def _save_data_from_link(self, url: str) -> ScrapeResult:
        """
        Extracts the data from the url.

        Args:
        - url (str): The URL of the link to extract data from.

        Returns:
        - the scrape result object

        Raises:
        - Exception: If there is an error during the scraping process.
        """
        display_logger = self.display_logger
        try:
            display_logger.debug(f"🔍 Getting scraper for: {url}")
            scraper = get_scraper(
                url=url,
                session=self.session,
                default_type=self.scraper_type,
                display_logger=display_logger,
            )
            dir = self._get_dir_for_url(url)
            display_logger.info(f"🔍 Trying to scrape: {url} to dir {dir}")
            scrape_result = scraper.scrape_to_file(url, dir)

            if scrape_result is None or scrape_result.rtn_code != ReturnCode.SUCCESS:
                if scrape_result is None:
                    display_logger.debug(
                        f"Initial scraper returned null result for: {url} "
                    )
                else:
                    display_logger.debug(
                        f"Initial scraper failed with rtn_code: {scrape_result.rtn_code}."
                    )

                fallback_scraper = self.settings.FALLBACK_SCRAPER
                if fallback_scraper and scraper.scraper_type() != fallback_scraper:
                    display_logger.debug(f"Trying fallback scraper {fallback_scraper}")
                    scraper = get_scraper(
                        url=url,
                        session=self.session,
                        default_type=fallback_scraper,
                        display_logger=display_logger,
                    )
                    scrape_result = scraper.scrape_to_file(url, dir)
                    display_logger.debug(
                        f"Fallback scraper returned null result for: {url} "
                        f"or failed rtn_code: {scrape_result.rtn_code}."
                    )

            if scrape_result is None:
                display_logger.debug(f"Returning an empty scrape result for {url}")
                return ScrapeResult(
                    url=url, file_path=None, rtn_code=ReturnCode.FAILURE_RETRY
                )

            if scrape_result.rtn_code != ReturnCode.SUCCESS:
                display_logger.debug(f"Returing the failed scrape result for: {url}")
                return scrape_result

            if scrape_result.reused:
                display_logger.info(f"🔄 Reused previously saved data: {url}")
            else:
                display_logger.info(f"✅ Scraped content from: {url}")
            return scrape_result
        except Exception as e:
            trace = traceback.format_exc()
            display_logger.debug(f"Error scraping (failure): {url} exception: {e}")
            display_logger.debug(f"Detailed error: {trace}")
            return ScrapeResult(
                url=url, file_path=None, rtn_code=ReturnCode.FAILURE_RETRY
            )
