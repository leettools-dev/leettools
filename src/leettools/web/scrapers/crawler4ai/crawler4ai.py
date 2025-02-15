import asyncio
from pathlib import Path
from typing import Optional

import requests
from crawl4ai import AsyncWebCrawler, CrawlResult

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import file_utils
from leettools.core.consts.return_code import ReturnCode
from leettools.web.schemas.scrape_result import ScrapeResult
from leettools.web.scrapers import scraper_utils
from leettools.web.scrapers.scraper import AbstractScraper


class Crawler4aiScraper(AbstractScraper):

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
        return "crawler4ai"

    async def _scrape_url(self, url: str) -> CrawlResult:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=url)
            return result

    def scrape_content_to_str(self, url: str) -> str:
        try:
            result = asyncio.run(self._scrape_url(url))
            if result is None:
                self.display_logger.error(f"Failed to scrape: {url}, return None")
                return ""
            if not result.success:
                self.display_logger.error(
                    f"Failed to scrape: {url}, error: {result.error_message}"
                )
                return ""
            return result.cleaned_html
        except Exception as e:
            self.display_logger.error(f"scrape_content_to_str {url}: {e}")
            return ""

    def scrape_to_file(self, url: str, dir: str) -> ScrapeResult:
        file_path = ""

        try:
            filename_prefix = file_utils.extract_filename_from_uri(url)
            suffix = file_utils.extract_file_suffix_from_url(url)
            if suffix != "":
                existing_scrape_result = scraper_utils.check_existing_file(
                    url=url,
                    dir=dir,
                    filename_prefix=filename_prefix,
                    suffix=suffix,
                    display_logger=self.display_logger,
                )
                if existing_scrape_result is not None:
                    return existing_scrape_result
                else:
                    self.display_logger.info(
                        f"No previous result found, need to scrape: {url} "
                        f"prefix {filename_prefix} suffix {suffix}"
                    )
            else:
                self.display_logger.info(
                    f"No suffix found, need to crawl first: {url}."
                )

            result = asyncio.run(self._scrape_url(url))
            if result is None:
                self.display_logger.error(f"Failed to scrape: {url}, return None")
                return ScrapeResult(
                    url=url,
                    file_path=None,
                    content=None,
                    reused=False,
                    rtn_code=ReturnCode.FAILURE_ABORT,
                )
            if not result.success:
                self.display_logger.error(
                    f"Failed to scrape: {url}, error: {result.error_message}"
                )
                return ScrapeResult(
                    url=url,
                    file_path=None,
                    content=None,
                    reused=False,
                    rtn_code=ReturnCode.FAILURE_ABORT,
                )

            # TODO: sometimes crawl4ai just returns html for other types of content
            # but its response_heasers are not set reliably
            if result.cleaned_html is not None:
                content = result.cleaned_html
            elif result.html is not None:
                content = result.html
            else:
                self.display_logger.error(f"Failed to scrape: {url}, no content")
                return ScrapeResult(
                    url=url,
                    file_path=None,
                    content=None,
                    reused=False,
                    rtn_code=ReturnCode.FAILURE_ABORT,
                )

            if not scraper_utils.is_content_length_ok(
                content, display_logger=self.display_logger
            ):
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
            existing_scrape_result = scraper_utils.check_existing_file(
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
                self.display_logger.debug(
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
                f"scrape_to_file exception {url} {file_path}: {e}"
            )
            return ScrapeResult(
                url=url,
                file_path=None,
                content=None,
                reused=False,
                rtn_code=ReturnCode.FAILURE_ABORT,
            )
