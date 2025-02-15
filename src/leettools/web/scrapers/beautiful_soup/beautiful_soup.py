from datetime import timedelta
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import file_utils, time_utils, url_utils
from leettools.core.consts.return_code import ReturnCode
from leettools.web.schemas.scrape_result import ScrapeResult
from leettools.web.scrapers.scraper import AbstractScraper
from leettools.web.scrapers.scraper_utils import (
    check_existing_file,
    save_url_content_to_file,
)


class BeautifulSoupSimpleScraper(AbstractScraper):

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

    def scraper_type(self) -> str:
        return "beautiful_soup_simple"

    def _is_content_length_ok(self, content: str) -> bool:
        from leettools.context_manager import ContextManager

        context = ContextManager().get_context()
        if context.is_test:
            self.display_logger.info(
                f"In the test mode. Ignoring the content length check."
            )
        else:
            if len(content) < 300:
                self.display_logger.info(
                    f"Content length is too short: {len(content)} characters"
                )
                self.display_logger.info(f"Short content: {content}")
                return False
        return True

    def scrape_content_to_str(self, url: str) -> str:
        try:
            response = self.session.get(url, timeout=4)
            soup = BeautifulSoup(response.content, "lxml", from_encoding="utf-8")

            for script_or_style in soup(["script"]):
                script_or_style.extract()

            raw_content = soup.prettify()
            return raw_content

        except Exception as e:
            self.display_logger.error(f"scrape_content_to_str {url}: {e}")
            return ""

    def scrape_to_file(self, url: str, dir: str) -> ScrapeResult:
        # TODO: use settings to set the default values of the parameters
        # such as size limit, timeout, etc.
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

            response = self.session.get(url, timeout=10)
            # check the type of the response
            content_type = response.headers.get("content-type")
            if content_type is None:
                self.display_logger.info(
                    f"Skipped scraping: {url}: content-type is None"
                )
                return ScrapeResult(
                    url=url,
                    file_path=None,
                    content=None,
                    reused=False,
                    rtn_code=ReturnCode.FAILURE_ABORT,
                )

            # if it is not an HTML file, save directly to the file
            if "text/html" not in content_type:
                content_type = response.headers.get("content-type")
                content = response.content
                return save_url_content_to_file(
                    url=url,
                    dir=dir,
                    content_type=content_type,
                    content=content,
                    display_logger=self.display_logger,
                )

            soup = BeautifulSoup(response.content, "lxml", from_encoding="utf-8")

            body_tag = soup.body
            # Extract the text content from the body
            if body_tag:
                body_text = body_tag.get_text()
                body_text = " ".join(body_text.split()).strip()
                if not self._is_content_length_ok(body_text):
                    return ScrapeResult(
                        url=url,
                        file_path=None,
                        content=body_text,
                        reused=False,
                        rtn_code=ReturnCode.FAILURE_ABORT,
                    )
            else:
                self.display_logger.info(
                    "Error scraping: {url}: No body tag found in the HTML document."
                )
                return ScrapeResult(
                    url=url,
                    file_path=None,
                    content=None,
                    reused=False,
                    rtn_code=ReturnCode.FAILURE_ABORT,
                )

            for script_or_style in soup(["script"]):
                script_or_style.extract()

            content = soup.prettify()

            if not self._is_content_length_ok(content):
                self.display_logger.info(
                    f"Error scraping: {url}: final content length too short: {content}"
                )
                return ScrapeResult(
                    url=url,
                    file_path=None,
                    content=content,
                    reused=False,
                    rtn_code=ReturnCode.FAILURE_ABORT,
                )

            suffix = "html"
            existing_scrape_result = check_existing_file(
                url=url,
                dir=dir,
                filename_prefix=filename_prefix,
                suffix=suffix,
                display_logger=self.display_logger,
            )
            if existing_scrape_result is not None:
                return existing_scrape_result

            timestamp = file_utils.filename_timestamp()
            file_path = f"{dir}/{filename_prefix}.{timestamp}.{suffix}"

            # if file already exists, print out an warning since this should not happen
            if Path(file_path).exists():
                self.display_logger.warning(
                    f"File with the same name and timestamp already exists: {file_path}"
                )

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ScrapeResult(
                url=url,
                file_path=file_path,
                content=content,
                reused=False,
                rtn_code=ReturnCode.SUCCESS,
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
