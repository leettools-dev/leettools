from typing import Optional

import requests
from newspaper import Article

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.web.scrapers.scraper import AbstractScraper


class NewspaperScraper(AbstractScraper):

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
        return "newspaper"

    def scrape_content_to_str(self, url: str) -> str:
        """
        This Python function scrapes an article from a given link, extracts the title
        and text content, and returns them concatenated with a colon.

        Returns:
          The `scrape` method returns a string that contains the title of the article
          followed by a colon and the text of the article. If the title or text is not
          present, an empty string is returned. If an exception occurs during the scraping
          process, an error message is printed and an empty string is returned.
        """
        try:
            article = Article(
                url,
                language="en",
                memoize_articles=False,
                fetch_images=False,
            )
            article.download()
            article.parse()

            title = article.title
            text = article.text

            # If title, summary are not present then return None
            if not (title and text):
                return ""

            return f"{title} : {text}"

        except Exception as e:
            self.display_logger.error("Error! : " + str(e))
            return ""
