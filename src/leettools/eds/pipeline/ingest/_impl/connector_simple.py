import os
import traceback
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import leettools.common.utils.url_utils
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.logging.logger_for_query import get_logger_for_chat
from leettools.common.utils import file_utils, time_utils
from leettools.common.utils.file_utils import file_hash_and_size, uri_to_path
from leettools.common.utils.url_utils import normalize_url
from leettools.context_manager import Context
from leettools.core.consts import flow_option
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.retriever_type import RetrieverType
from leettools.core.consts.return_code import ReturnCode
from leettools.core.repo.docsink_store import AbstractDocsinkStore
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSource, IngestConfig
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.pipeline.ingest.connector import AbstractConnector
from leettools.settings import (
    DOCX_EXT,
    PDF_EXT,
    PPTX_EXT,
    XLSX_EXT,
    supported_file_extensions,
)
from leettools.web.schemas.scrape_result import ScrapeResult
from leettools.web.web_scraper import WebScraper
from leettools.web.web_searcher import WebSearcher


class ConnectorSimple(AbstractConnector):
    """
    ConnectorSimple is a simple connector that ingests a document
    source and saves the content to a local folder.
    """

    def __init__(
        self,
        context: Context,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
        docsinkstore: AbstractDocsinkStore,
        display_logger: Optional[EventLogger] = None,
    ) -> None:
        """
        Initializes the ConnectorSimple class.

        Args:
        - context (Context): The context object.
        - org (Org): The organization object.
        - kb (KnowledgeBase): The knowledge base object.
        - docsource (DocSource): The document source object.
        - docsinkstore (AbstractDocsinkStore): The docsink store object.
        - display_logger (Optional[EventLogger]): The display logger object.

        Returns:
        - None
        """
        self.context = context
        self.org = org
        self.kb = kb
        self.kb_id = docsource.kb_id  # we can remove the kb_id in docsource later

        self.docsource = docsource
        self.docsource_uri = docsource.uri

        self.docsource_type = docsource.source_type
        self.visited: set = set()
        self.docsink_create_list: Optional[List[DocSinkCreate]] = []
        self.docsinkstore = docsinkstore
        self.local_folder = os.path.join(
            context.settings.DOCSINK_LOCAL_DIR,
            org.org_id,
            kb.kb_id,
            docsource.docsource_uuid,
        )
        self.log_location: str = None
        if not os.path.exists(self.local_folder):
            os.makedirs(self.local_folder)

        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
        )

        if display_logger is not None:
            self.display_logger = display_logger
        else:
            self.display_logger = logger()

    def _scrape_url(self, url: str) -> str:
        """
        Scrapes the given URL and returns the scrape result.

        Args:
        - url (str): The URL to be scraped.

        Returns:
        - str: The scrape result. None if an error occurs during the scraping process.
        """
        try:
            self.display_logger.info(f"Scraping urls... {url}")
            urls = [url]
            scrape_results = WebScraper(
                context=self.context,
                user_agent=self.user_agent,
                display_logger=self.display_logger,
            ).scrape_urls_to_file(urls)
        except Exception as e:
            self.display_logger.error(f"Error in scrape_urls: {e}")
            return None
        if len(scrape_results) != 1:
            self.display_logger.error(
                f"Expecting one scrape result, but got: {scrape_results}"
            )
            return None
        content = scrape_results[0].get("raw_content", None)
        return content

    def _copy_file_to_local(self, src: str, dest: str) -> bool:
        """
        Copies a file from the source to the destination.

        Args:
        - src: The source file.
        - dest: The destination file.
        """
        # create parent directories if they do not exist
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(src, "rb") as f:
            with open(dest, "wb") as d:
                d.write(f.read())
        return True

    def _is_internal_url(self, url: str) -> bool:
        """
        Checks if the URL is in the same TLD as the docsource URI.

        Args:
            url: The URL to be checked.

        Returns:
            True if the URL is internal, False otherwise.
        """
        tld = leettools.common.utils.url_utils.get_first_level_domain_from_url(url)
        base_tld = leettools.common.utils.url_utils.get_first_level_domain_from_url(
            self.docsource_uri
        )

        if tld == base_tld:
            return True
        return False

    def _is_hyperlink_file(self, url: str) -> bool:
        """
        Checks if the URL is a hyperlink file.

        Args:
            url: The URL to be checked.

        Returns:
            True if the URL is a hyperlink file, False otherwise.
        """
        url_str = str(url).lower()
        if (
            url_str.endswith(".html")
            or url_str.endswith(".htm")
            or url_str.endswith(".php")
            or url_str.endswith(".asp")
        ):
            return True
        else:
            return False

    def _is_supported_file(self, url: str) -> bool:
        """
        Checks if the URL is a supported file.

        Args:
            url: The URL to be checked.

        Returns:
            True if the URL is a supported file, False otherwise.
        """
        url_str = str(url).lower()
        if (
            url_str.endswith(DOCX_EXT)
            or url_str.endswith(PDF_EXT)
            or url_str.endswith(PPTX_EXT)
            or url_str.endswith(XLSX_EXT)
        ):
            return True
        else:
            return False

    def _ingest_file_or_folder(self) -> None:
        """
        Ingests a file or folder.
        """
        path = uri_to_path(self.docsource_uri)
        self.display_logger.debug(f"Ingesting {self.docsource_uri}")
        if path.exists():
            self.display_logger.debug(f"Ingesting {self.docsource_uri}, path exists")
            if path.is_file():
                self.display_logger.debug(f"Ingesting {self.docsource_uri}, is file")
                if (
                    self.docsource_type == DocSourceType.FILE
                    or self.docsource_type == DocSourceType.AUDIO
                    or self.docsource_type == DocSourceType.IMG
                    or self.docsource_type == DocSourceType.VID
                ):
                    self.display_logger.info(
                        f"Processing uploaded file: {self.docsource_uri}"
                    )
                    self._ingest_file(self.docsource_uri)
                else:
                    self.display_logger.info(
                        f"Processing local file: {self.docsource_uri}"
                    )
                    self._ingest_file(self.docsource_uri, is_local=True)
            elif path.is_dir():
                self.display_logger.debug(f"Ingesting {self.docsource_uri}, is_dir")
                if (
                    self.docsource_type == DocSourceType.FILE
                    or self.docsource_type == DocSourceType.AUDIO
                    or self.docsource_type == DocSourceType.IMG
                    or self.docsource_type == DocSourceType.VID
                ):
                    self.display_logger.info(
                        f"Processing uploaded folder: {self.docsource_uri}"
                    )
                    self._ingest_folder(self.docsource_uri)
                    self.display_logger.info(
                        f"Processing load folder: {self.docsource_uri}"
                    )
                elif self.docsource_type == DocSourceType.LOCAL:
                    self.display_logger.info(
                        f"Ingesting {self.docsource_uri}, ingesting local folder"
                    )
                    self._ingest_folder(self.docsource_uri, is_local=True)
                else:
                    self.display_logger.error(
                        f"Unsupported docsource type for folder: {self.docsource_type}"
                    )
            else:
                self.display_logger.error(
                    f"{self.docsource_uri} is not a file or folder."
                )
        else:
            self.display_logger.error(f"Path does not exist: {self.docsource_uri}")

    def _ingest_file(self, file_path: str, is_local: bool = False) -> bool:
        """
        Ingests a file.

        Args:
        file_path: The path to the uploaded file.
        is_local: Whether the file is local.

        Returns:
        True if the file was ingested successfully, False otherwise.
        """
        if is_local:
            if file_path.startswith("file://"):
                file_uri = file_path
                file_path = file_path[7:]
            else:
                file_uri = Path(file_path).as_uri()
            doc_hash, doc_size = file_hash_and_size(Path(file_path))
            docsink_create = DocSinkCreate(
                docsource=self.docsource,
                original_doc_uri=file_uri,
                raw_doc_uri=file_path,
                raw_doc_hash=doc_hash,
                size=doc_size,
            )
            self.docsink_create_list.append(docsink_create)
            return True

        if file_path.startswith("file://"):
            file_path = file_path[7:]

        if self.docsource_uri.startswith("file://"):
            docsource_uri = self.docsource_uri[7:]
        else:
            docsource_uri = self.docsource_uri

        # get the relative path of the file from the docsource_uri,
        # which should not include the file basename
        relative_path = os.path.relpath(file_path, docsource_uri)
        relative_dir_path = os.path.dirname(relative_path)

        # create the destination path
        filename = os.path.basename(file_path)
        if relative_path == ".":
            relative_path = ""

        dest = os.path.join(self.local_folder, relative_dir_path, filename)
        if self._copy_file_to_local(file_path, dest):
            self.display_logger.info(f"Finished copying {file_path} to {dest}")
            doc_hash, doc_size = file_hash_and_size(Path(dest))
            docsink_create = DocSinkCreate(
                docsource=self.docsource,
                original_doc_uri=file_path,
                raw_doc_uri=dest,
                raw_doc_hash=doc_hash,
                size=doc_size,
            )
            self.docsink_create_list.append(docsink_create)
            return True
        else:
            self.display_logger.error(f"Failed to copy file: {self.docsource_uri}")
            return False

    def _ingest_folder(self, dir_uri: str, is_local: bool = False) -> None:
        """
        Ingests a folder.

        Args:
        - dir_uri: The path to the folder.
        - is_local: Whether the folder is local.
        """
        if is_local:
            dir_path = uri_to_path(dir_uri)
        else:
            dir_path = Path(dir_uri)

        # check if self.docsource_uri is a folder
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_name, file_extension = os.path.splitext(file)
                if file_extension not in supported_file_extensions():
                    continue
                file_path = os.path.join(root, file)
                self._ingest_file(file_path, is_local)

    def _ingest_url(self, url: str) -> ScrapeResult:
        """
        Ingest the content from the URL to a local file.

        Args:
            url: The URL from which the content is to be saved.

        Returns:
            The ScrapeResult object. None if an error occurs during the ingesting process.
        """
        url_str = str(url)
        self.display_logger.info(f"Retrieving content from {url_str}")

        # check if the URL is a valid http or https URL
        if not url_str.startswith("http://") and not url_str.startswith("https://"):
            self.display_logger.warning(
                f"URL not starting with http:// or https://, adding https:// as default."
            )
            url_str = f"https://{url_str}"

        web_scraper = WebScraper(
            context=self.context,
            user_agent=self.user_agent,
            display_logger=self.display_logger,
        )
        results = web_scraper.scrape_urls_to_file([url_str])
        if len(results) != 1:
            self.display_logger.error(f"Expected one scrape result, but got: {results}")
            return ScrapeResult(
                url=url,
                file_path=None,
                content=None,
                reused=False,
                rtn_code=ReturnCode.FAILURE_ABORT,
            )

        scrape_result = results[0]
        if (
            scrape_result.rtn_code is not None
            and scrape_result.rtn_code != ReturnCode.SUCCESS
        ):
            self.display_logger.error(
                f"Failed to scrape {url}: {scrape_result.rtn_code}"
            )
            return scrape_result

        file_path = scrape_result.file_path

        doc_hash, doc_size = file_hash_and_size(Path(file_path))

        docsink_create = DocSinkCreate(
            docsource=self.docsource,
            original_doc_uri=url,
            raw_doc_uri=file_path,
            raw_doc_hash=doc_hash,
            size=doc_size,
        )
        self.docsink_create_list.append(docsink_create)
        self.display_logger.info(f"Saved {url} to {file_path}")
        return scrape_result

    def _ingest_website(
        self,
        url: str,
        crawled_urls: Dict[str, bool],
        depth: int,
        ingest_config: IngestConfig,
    ) -> None:
        """
        Crawls the website and saves the content to a local folder.

        Args:
        - url: The URL of the website to be crawled.
        - crawled_urls: A dictionary of crawled URLs.
        - depth: The depth of the crawl.
        - ingest_config: The ingestion configuration.

        """
        if ingest_config.extra_parameters is None:
            extra_parameters = {}
        else:
            extra_parameters = ingest_config.extra_parameters

        max_depth = int(extra_parameters.get("max_depth", 3))
        max_url = int(extra_parameters.get("max_urls", 20))

        self.display_logger.info(
            f"Processing website: {url}, current depth: {depth}, "
            f"max_depth: {max_depth}, max_url: {max_url} "
            f"current crawled_urls: {len(crawled_urls)}"
        )

        normalized_url = normalize_url(url)

        if not self._is_internal_url(normalized_url):
            self.display_logger.info(f"Skipping outside URL: {normalized_url}")
            return

        if normalized_url in self.visited:
            self.display_logger.info(f"URL already visited: {normalized_url}")
            return

        scrape_result = self._ingest_url(normalized_url)
        if scrape_result is None:
            self.display_logger.error(f"Failed to crawl url: {normalized_url}")
            return
        crawled_urls[normalized_url] = True

        if not scrape_result.content:
            self.display_logger.info(f"No content retrieved for url: {normalized_url}")
            return

        if not self._is_hyperlink_file(scrape_result.file_path):
            self.display_logger.info(
                f"Skipping link checking for file: {scrape_result.file_path}"
            )
            return

        if depth >= max_depth:
            self.display_logger.info(f"Skipping link checking at max depth: {depth}")
            return

        if len(crawled_urls) >= max_url:
            self.display_logger.info(
                f"Skipping link checking at max url: {len(crawled_urls)}"
            )
            return

        # TODO: we are basically doing a depth-first search here
        # Maybe we should use breadth-first search by default
        # https://github.com/LinkTime-Corp/leettools/issues/1035
        try:
            top_tld = leettools.common.utils.url_utils.get_first_level_domain_from_url(
                normalized_url
            )

            self.display_logger.info(f"Finding links in {normalized_url}")

            # response = requests.get(normalized_url, timeout=100)
            # response.raise_for_status()
            # soup = BeautifulSoup(response.text, "html.parser")

            soup = BeautifulSoup(scrape_result.content, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link.get("href")
                joined_url = urljoin(normalized_url, href)
                self.display_logger.debug(
                    f"Joined URL: {joined_url} from base: {normalized_url} and relatvie: {href}"
                )
                full_url = normalize_url(joined_url)

                # if the new url is in the same domain and not visited
                tld = leettools.common.utils.url_utils.get_first_level_domain_from_url(
                    full_url
                )
                if tld == top_tld:
                    if full_url not in crawled_urls:
                        self.display_logger.info(
                            f"Found new link in same tld: {full_url}"
                        )
                    else:
                        self.display_logger.debug(f"Skipping visited link: {full_url}")
                        continue
                else:
                    self.display_logger.debug(f"Skipping different tld: {full_url}")
                    continue

                self._ingest_website(
                    url=full_url,
                    crawled_urls=crawled_urls,
                    depth=depth + 1,
                    ingest_config=ingest_config,
                )
        except requests.RequestException as e:
            self.display_logger.error(f"Failed to crawl {url}: {str(e)}")

    def _run_search(self) -> None:
        web_searcher = WebSearcher(context=self.context)

        # TODO: the connector should run with correct user and options
        uri = self.docsource.uri
        if not uri.startswith("search://"):
            raise exceptions.UnexpectedCaseException(
                f"Search docsource URI ({uri}) should start with search://"
            )
        params = file_utils.parse_uri_for_search_params(uri)
        query = params.get("q", None)
        if query is None:
            raise exceptions.UnexpectedCaseException(
                f"No query found in search URI {uri}"
            )

        flow_options = {}
        chat_id = None
        query_id = None

        if self.docsource.ingest_config is not None:
            flow_options = self.docsource.ingest_config.flow_options
            if flow_options is not None and flow_options != {}:
                self.display_logger.info(
                    f"Using flow options from docsource: {flow_options}"
                )
            else:
                flow_options = {}
            extra_parameters = self.docsource.ingest_config.extra_parameters
            if extra_parameters:
                chat_id = extra_parameters.get("chat_id", None)
                query_id = extra_parameters.get("query_id", None)

        if flow_options == {}:
            try:
                retriever_type = RetrieverType(params["provider"]).value
            except KeyError:
                retriever_type = RetrieverType.GOOGLE.value
            date_range_para = params.get("date_range", None)
            if date_range_para is None:
                days_limit = 0
            else:
                days_limit = int(date_range_para)

            max_results_para = params.get("max_results", 10)
            if max_results_para is None:
                max_results = 10
            else:
                max_results = int(max_results_para)

            flow_options[flow_option.FLOW_OPTION_RETRIEVER_TYPE] = retriever_type
            flow_options[flow_option.FLOW_OPTION_DAYS_LIMIT] = days_limit
            flow_options[flow_option.FLOW_OPTION_SEARCH_MAX_RESULTS] = max_results

        # we need that in the DocSource IngestionConfig
        if chat_id is None or query_id is None:
            chat_logger = self.display_logger
        else:
            _, chat_logger = get_logger_for_chat(
                chat_id=chat_id,
                query_id=query_id,
            )

        user = User.get_admin_user()
        self.docsink_create_list = web_searcher.create_docsinks_by_search_and_scrape(
            context=self.context,
            org=self.org,
            kb=self.kb,
            user=user,
            search_keywords=query,
            docsource=self.docsource,
            flow_options=flow_options,
            display_logger=chat_logger,
        )

    def _ingest(self) -> ReturnCode:
        if self.docsource_type == DocSourceType.URL:
            scrape_result = self._ingest_url(self.docsource_uri)
            if scrape_result is not None:
                self.display_logger.info(
                    f"Finished saving URL {self.docsource_uri}  "
                    f"to file {scrape_result.file_path}"
                )
            else:
                self.display_logger.error(f"Failed to crawl url: {self.docsource_uri}")
                self.docsink_create_list = []

        elif self.docsource_type == DocSourceType.WEB:
            # Note: we don't fail the whole ingestion if one of the URLs fails
            if self.docsource.ingest_config is None:
                self.display_logger.warning(
                    "Ingest config is missing for web site docsource. Using defaualt."
                )
                default_max_depth = self.context.settings.WEB_SITE_CRAWL_DEPTH
                default_max_urls = self.context.settings.WEB_SITE_CRAWL_MAX_URLS
                ingest_config = IngestConfig(
                    extra_parameters={
                        "max_depth": default_max_depth,
                        "max_urls": default_max_urls,
                    }
                )
            else:
                ingest_config = self.docsource.ingest_config

            crawled_urls: Dict[str, bool] = {}
            self._ingest_website(
                url=self.docsource_uri,
                crawled_urls=crawled_urls,
                depth=1,
                ingest_config=ingest_config,
            )
            self.display_logger.info(f"Finished crawling web site {self.docsource_uri}")

        elif (
            self.docsource_type == DocSourceType.FILE
            or self.docsource_type == DocSourceType.LOCAL
            or self.docsource_type == DocSourceType.AUDIO
            or self.docsource_type == DocSourceType.IMG
            or self.docsource_type == DocSourceType.VID
        ):
            self._ingest_file_or_folder()
        elif self.docsource_type == DocSourceType.SEARCH:
            self.display_logger.info("Search docsource type is handled in application.")
            self._run_search()
        else:
            self.display_logger.error(
                f"Unsupported docsource type: {self.docsource_type}"
            )

        if len(self.docsink_create_list) == 0:
            self.display_logger.error("No docsink were created.")
            return ReturnCode.FAILURE

        ingested_count = 0
        reused_count = 0
        cur_time = time_utils.current_datetime()
        for docsink_create in self.docsink_create_list:
            docsink = self.docsinkstore.create_docsink(
                self.org, self.kb, docsink_create
            )
            if docsink is not None:
                if docsink.created_at < cur_time:
                    reused_count += 1
                else:
                    ingested_count += 1
            else:
                self.display_logger.info(
                    f"Failed to create new docsink: {docsink_create.raw_doc_uri}"
                )
        self.display_logger.info(
            f"Ingestion successful: new docsinks {ingested_count}, reused docsinks: {reused_count}."
        )
        return ReturnCode.SUCCESS

    def get_ingested_docsink_list(self) -> Optional[List[DocSinkCreate]]:
        return self.docsink_create_list

    def ingest(self) -> ReturnCode:
        if self.log_location:
            log_handler = self.display_logger.log_to_file(self.log_location)
        else:
            log_handler = None
        try:
            rtn_code = self._ingest()
            return rtn_code
        except Exception as e:
            trace = traceback.format_exc()
            self.display_logger.error(f"Error ingesting docsource: {trace}")
            return ReturnCode.FAILURE
        finally:
            if log_handler:
                self.display_logger.remove_file_handler()

    def set_log_location(self, log_location: str) -> None:
        self.log_location = log_location
