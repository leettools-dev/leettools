from typing import Optional

import requests
from langchain_community.document_loaders import WebBaseLoader

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.web.scrapers.scraper import AbstractScraper


class WebBaseLoaderScraper(AbstractScraper):

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
        return "web_base_loader"

    def scrape_content_to_str(self, url: str) -> str:
        """
        This Python function scrapes content from a webpage using a WebBaseLoader object
        and returns the concatenated page content.

        Returns:
          The `scrape` method is returning a string variable named `content` which contains
          the concatenated page content from the documents loaded by the `WebBaseLoader`.
          If an exception occurs during the process, an error message is printed and an
          empty string is returned.
        """
        try:
            loader = WebBaseLoader(url)
            loader.requests_kwargs = {"verify": False}
            docs = loader.load()
            content = ""

            for doc in docs:
                content += doc.page_content

            return content

        except Exception as e:
            self.display_logger.error("Error! : " + str(e))
            return ""
