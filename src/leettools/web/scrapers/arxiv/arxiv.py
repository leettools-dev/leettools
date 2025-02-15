from typing import Optional

import requests
from langchain_community.retrievers import ArxivRetriever

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import file_utils
from leettools.web.schemas.scrape_result import ScrapeResult
from leettools.web.scrapers.scraper import AbstractScraper


class ArxivScraper(AbstractScraper):

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
        return "arxiv"

    def scrape_content_to_str(self, url: str) -> str:
        """
        The function scrapes relevant documents from Arxiv based on a given link and
        returns the content of the first document.

        Returns:
          The code is returning the page content of the first document retrieved by the
          ArxivRetriever for a given query extracted from the link.
        """
        query = url.split("/")[-1]
        retriever = ArxivRetriever(load_max_docs=2, doc_content_chars_max=None)
        docs = retriever.get_relevant_documents(query=query)
        return docs[0].page_content

    def scrape_to_file(self, url: str, dir: str) -> ScrapeResult:
        file_path = ""

        try:
            suffix = "txt"
            filename_prefix = file_utils.extract_filename_from_uri(url)
            timestamp = file_utils.filename_timestamp()
            file_path = f"{dir}/{filename_prefix}.{timestamp}.{suffix}"

            content = self.scrape_content_to_str(url)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)

            return ScrapeResult(url=url, file_path=file_path, content=content)

        except Exception as e:
            self.display_logger.warning(
                f"scrape_to_file exception {url} {file_path}: {e}"
            )
            return None
