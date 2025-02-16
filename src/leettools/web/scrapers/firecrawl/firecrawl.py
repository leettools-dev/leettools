from typing import Optional

import requests
from firecrawl import FirecrawlApp

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import file_utils
from leettools.context_manager import ContextManager
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.user import User
from leettools.core.user.user_settings_helper import get_value_from_settings
from leettools.web.schemas.scrape_result import ScrapeResult
from leettools.web.scrapers.scraper import AbstractScraper
from leettools.web.scrapers.scraper_utils import (
    check_existing_file,
    save_url_content_to_file,
)


class FirecrawlScraper(AbstractScraper):
    """
    Firecrawl Scraper
    """

    def __init__(
        self,
        session: requests.Session = None,
        display_logger: Optional[EventLogger] = None,
    ):
        self.session = session
        if display_logger is not None:
            self.display_logger = display_logger
        else:
            self.display_logger = logger()
        self.api_key = self._get_api_key()
        self.api_url = self._get_api_url()
        self.app = FirecrawlApp(api_key=self.api_key, api_url=self.api_url)

    def scraper_type(self) -> str:
        return "firecrawl"

    def scrape_content_to_str(self, url: str) -> str:
        data = self.app.scrape_url(url)
        if data is not None:
            if isinstance(data, dict):
                metadata = data.get("metadata", {})
                status_code = metadata.get("statusCode", None)
                markdown = data.get("markdown", None)
                if status_code == 200:
                    if markdown is not None:
                        return markdown
                    else:
                        self.display_logger.debug(
                            f"Failed to FireCrawl {url}: no markdown content"
                        )
                else:
                    self.display_logger.debug(
                        f"Failed to FireCrawl {url}: status code {status_code}"
                    )
            else:
                self.display_logger.debug(
                    f"Failed to FireCrawl {url}: unexpected data type {type(data)}"
                )
        else:
            self.display_logger.debug(f"Failed to FireCrawl {url}: no data")
        return ""

    def scrape_to_file(self, url: str, dir: str) -> ScrapeResult:
        file_path = ""

        try:
            filename_prefix = file_utils.extract_filename_from_uri(url)
            suffix = file_utils.extract_file_suffix_from_url(url)
            if suffix != "":
                existing_scrape_result = check_existing_file(
                    url=url,
                    dir=dir,
                    filename_prefix=filename_prefix,
                    suffix=suffix,
                    display_logger=self.display_logger,
                )
                if existing_scrape_result is not None:
                    return existing_scrape_result
                else:
                    self.display_logger.debug(
                        f"No previous result found, need to scrape: {url} "
                        f"prefix {filename_prefix} suffix {suffix}"
                    )
            else:
                self.display_logger.debug(
                    f"No suffix found, need to crawl first: {url}."
                )

            content = self.scrape_content_to_str(url)
            if content == "":
                return ScrapeResult(
                    url=url,
                    file_path=None,
                    content=None,
                    reused=False,
                    rtn_code=ReturnCode.FAILURE_ABORT,
                )

            return save_url_content_to_file(
                url=url,
                dir=dir,
                content_type="markdown",
                content=content,
                display_logger=self.display_logger,
            )
        except Exception as e:
            self.display_logger.warning(
                f"Exception scrape_to_file {url} {file_path}: {e}"
            )
            return ScrapeResult(
                url=url,
                file_path=None,
                content=None,
                reused=False,
                rtn_code=ReturnCode.FAILURE_ABORT,
            )

    def _get_api_key(self) -> str:
        try:
            context = ContextManager().get_context()
            # right now scrapers don't have user, so we are using admin user settings
            user = User.get_admin_user()
            user_settings = context.get_user_settings_store().get_settings_for_user(
                user
            )
            # the get_value_from_settings will fall back to admin_user settings
            # if the user settings has no keys
            api_key = get_value_from_settings(
                context=context,
                user_settings=user_settings,
                default_env="FIRECRAWL_API_KEY",
                first_key="FIRECRAWL_API_KEY",
                second_key=None,
                allow_empty=False,
            )
        except Exception as e:
            self.display_logger.debug(
                "Failed to get FireCrawl API key. Maybe using a proxy, set the dummp key "
                "instead. If possible, please set the EDS_FIRECRAWL_API_KEY environment variable. "
                f"{e}"
            )
            raise e
        return api_key

    def _get_api_url(self) -> str:
        try:
            context = ContextManager().get_context()
            user = User.get_admin_user()
            user_settings = context.get_user_settings_store().get_settings_for_user(
                user
            )
            # the get_value_from_settings will fall back to admin_user settings
            # if the user settings has no keys
            api_url = get_value_from_settings(
                context=context,
                user_settings=user_settings,
                default_env="FIRECRAWL_API_URL",
                first_key="FIRECRAWL_API_URL",
                second_key=None,
                allow_empty=True,
            )
            if api_url is None or api_url == "":
                api_url = "https://api.firecrawl.dev"
        except Exception as e:
            self.display_logger.debug(
                "Failed to get FireCrawl API URL. Using the default URL. "
            )
            api_url = "https://api.firecrawl.dev"
        return api_url
