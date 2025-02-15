from typing import Optional

import requests
from langchain_community.document_loaders import PyMuPDFLoader

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import file_utils
from leettools.web.schemas.scrape_result import ScrapeResult
from leettools.web.scrapers.scraper import AbstractScraper


class PyMuPDFScraper(AbstractScraper):

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
        return "pymupdf"

    def scrape_content_to_str(self, url: str) -> str:
        """
        The `scrape` function uses PyMuPDFLoader to load a document from a given link
        and returns it as a string.

        Returns:
          The `scrape` method is returning a string representation of the `doc` object,
          which is loaded using PyMuPDFLoader from the provided link.
        """
        loader = PyMuPDFLoader(url)
        doc = loader.load()
        return str(doc)

    def scrape_to_file(self, url: str, dir: str) -> ScrapeResult:
        file_path = ""

        try:
            suffix = "pdf"
            filename_prefix = file_utils.extract_filename_from_uri(url)
            timestamp = file_utils.filename_timestamp()
            file_path = f"{dir}/{filename_prefix}.{timestamp}.{suffix}"

            response = requests.get(url)
            with open(file_path, "wb") as file:
                file.write(response.content)

            # TODO: here we just write the file to the disk without reading the content
            return ScrapeResult(url=url, file_path=file_path, content=None)

        except Exception as e:
            self.display_logger.warning(
                f"scrape_to_file exception {url} {file_path}: {e}"
            )
            return None
