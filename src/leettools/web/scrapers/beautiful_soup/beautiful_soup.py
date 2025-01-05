from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import file_utils, time_utils, url_utils
from leettools.core.consts.return_code import ReturnCode
from leettools.web.schemas.scrape_result import ScrapeResult
from leettools.web.scrapers.scrapper import AbstractScrapper


class BeautifulSoupSimpleScraper(AbstractScrapper):

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

    def _check_existing_file(
        self, url: str, dir: str, filename_prefix: str, suffix: str
    ) -> ScrapeResult:
        existing_file_list = file_utils.get_files_with_timestamp(
            dir, filename_prefix, suffix
        )
        if existing_file_list:
            latest_file, ts = existing_file_list[0]
            self.display_logger.debug(
                f"File with the same name and suffix already exists: {latest_file}, "
                f"timestamp: {ts}"
            )
            # if the latest file is less than 1 day old, skip the scraping
            now = time_utils.current_datetime()
            diff: timedelta = now - ts
            # TODO: make the delta configurable
            if diff.days < 1:
                self.display_logger.debug(
                    f"Skipping saving: {url}: file already exists and is less than 1 day old"
                )
                file_path = f"{dir}/{latest_file}"
                # TODO: maybe we can check the content length here
                return ScrapeResult(
                    url=url,
                    file_path=file_path,
                    content=None,
                    reused=True,
                    rtn_code=ReturnCode.SUCCESS,
                )
            else:
                self.display_logger.debug(
                    f"File is older than 1 day, scraping again: {url}"
                )
                return None
        else:
            return None

    def _save_url_content_to_file(
        self, url: str, dir: str, response: requests.Response
    ) -> ScrapeResult:
        file_path = ""
        try:
            content_type = response.headers.get("content-type")
            suffix = url_utils.content_type_to_ext.get(content_type, "unknown.dat")
            self.display_logger.info(
                f"Non-html content_type: {content_type}, suffix: {suffix}"
            )
            filename_prefix = file_utils.extract_filename_from_uri(url)

            # check if there is a file with the same name and suffix in the directory
            existing_scrape_result = self._check_existing_file(
                url=url, dir=dir, filename_prefix=filename_prefix, suffix=suffix
            )
            if existing_scrape_result:
                return existing_scrape_result

            timestamp = file_utils.filename_timestamp()
            file_path = f"{dir}/{filename_prefix}.{timestamp}.{suffix}"

            with open(file_path, "wb") as file:
                file.write(response.content)

            # TODO: here we just write the file to the disk without reading the content
            return ScrapeResult(
                url=url,
                file_path=file_path,
                content=None,
                reused=False,
                rtn_code=ReturnCode.SUCCESS,
            )
        except Exception as e:
            self.display_logger.warning(f"scrape_to_file {url} {file_path}: {e}")
            return ScrapeResult(
                url=url,
                file_path=file_path,
                content=None,
                reused=False,
                rtn_code=ReturnCode.FAILURE_ABORT,
            )

    def scrape_to_file(self, url: str, dir: str) -> ScrapeResult:
        # TODO: use settings to set the default values of the parameters
        # such as size limit, timeout, etc.
        file_path = ""

        try:
            filename_prefix = file_utils.extract_filename_from_uri(url)
            suffix = file_utils.extract_file_suffix_from_url(url)
            if suffix != "":
                existing_scrape_result = self._check_existing_file(
                    url=url, dir=dir, filename_prefix=filename_prefix, suffix=suffix
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
                return self._save_url_content_to_file(url, dir, response)

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
            existing_scrape_result = self._check_existing_file(
                url=url, dir=dir, filename_prefix=filename_prefix, suffix=suffix
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
            self.display_logger.warning(f"scrape_to_file {url} {file_path}: {e}")
            return ScrapeResult(
                url=url,
                file_path=None,
                content=None,
                reused=False,
                rtn_code=ReturnCode.FAILURE_ABORT,
            )
