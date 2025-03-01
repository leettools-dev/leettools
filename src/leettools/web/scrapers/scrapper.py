from abc import ABC, abstractmethod
from typing import Optional

import requests

from leettools.common.logging.event_logger import EventLogger
from leettools.web.schemas.scrape_result import ScrapeResult


class AbstractScrapper(ABC):
    """
    The `AbstractScrapper` class is an abstract base class that defines the interface
    for all scrapper classes.

    The main API function is the `scrape` method that scrapes content from a webpage
    specified by the `url` argument and return the cleaned content as a string.
    """

    @abstractmethod
    def __init__(
        self,
        session: requests.Session = None,
        display_logger: Optional[EventLogger] = None,
    ):
        pass

    @abstractmethod
    def scrape_content_to_str(self, url: str) -> str:
        """
        The `scrape_content_to_str` method should scrape the content from the webpage
        specified by the `url` argument and return the cleaned content as a string.

        We prefer the scrape_to_file method to be used instead of this method since
        in many cases we need to save the file first and then extract the content using
        different methods.

        Args:
        - url (str): The URL of the webpage from which the content should be scraped.

        Returns:
        - str: The cleaned content extracted from the webpage specified by the `url` argument.
        """
        pass

    @abstractmethod
    def scrape_to_file(self, url: str, dir: str) -> ScrapeResult:
        """
        The `scrape_to_file` method should scrape the content from the webpage specified
        by the `url` argument and save the content to the file specified by the `file_path`
        argument.

        Args:
        - url (str): The URL of the webpage from which the content should be scraped.
        - dir (str): The dir where the scraped content should be saved.

        Returns:
        - the final ScrapeResult with the file path and the content.
        """
        pass

    @abstractmethod
    def scraper_type(self) -> str:
        """
        The `scraper_type` method is an abstract method that should be implemented by
        the child classes. The method should return the type of the scraper class.

        Returns:
        - str: The type of the scraper class.
        """
        pass


def get_scraper(
    url: str,
    session: requests.Session,
    default_type: str,
    display_logger: Optional[EventLogger] = None,
) -> AbstractScrapper:
    """
    The function `get_scraper` determines the appropriate scraper class based on the
    provided link or a default scraper if none matches.

    Args:
    - url (str): The URL of the webpage to scrape.
    - session (requests.Session): The requests session object.
    - default_type (str): The default scraper type to use if no match is found.
    - display_logger (Optional[EventLogger]): The display logger.

    Returns:
    - The `get_scraper` method returns the scraper class based on the provided link.
      The method checks the link to determine the appropriate scraper class to use
      based on predefined mappings in the `SCRAPER_CLASSES` dictionary. If the link
      ends with ".pdf", it selects the `PyMuPDFScraper` class. If the link contains
      "arxiv.org", it selects the `ArxivScraper`.
    """
    scraper_type = None

    if url.endswith(".pdf"):
        scraper_type = "pymupdf"
    elif "arxiv.org" in url:
        if "/pdf/" in url:
            scraper_type = "pymupdf"
        elif "/abs/" in url:
            scraper_type = "arxiv"
        else:
            scraper_type = default_type
    else:
        scraper_type = default_type

    from leettools.common.utils import factory_util

    module_name = f"{__package__}.{scraper_type}.{scraper_type}"

    return factory_util.create_object(
        module_name=module_name,
        base_class=AbstractScrapper,
        session=session,
        display_logger=display_logger,
    )
