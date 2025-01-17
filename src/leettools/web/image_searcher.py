import os
import uuid
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel

from leettools.common.logging import EventLogger, logger
from leettools.common.utils import config_utils, file_utils
from leettools.context_manager import Context
from leettools.core.consts import flow_option
from leettools.core.consts.retriever_type import RetrieverType
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.web.retrievers.retriever import create_retriever


class ImageSearchResult(BaseModel):
    image_url: str
    image_path: str
    caption: Optional[str] = ""


class ImageSearcher:
    """
    Search for images using a given query.
    """

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):

        self.context = context
        self.org = org
        self.kb = kb
        self.user = user
        self.output_root = f"{context.settings.DATA_ROOT}/imagesearch"
        self.logger = logger()  # default logger

    def _get_new_urls(
        self,
        visited_urls: Dict[str, str],
        url_list: List[str],
        display_logger: EventLogger,
    ) -> list[str]:
        """
        Gets the new urls from the given url set.
        Args:
        - visited_urls (Dict[str, str]): The url list to check
        - url_list (List[str]): The url list to check
        - display_logger (EventLogger): The logger to use for displaying messages

        Returns:
        - list[str]: The new urls from the given url set
        """

        new_urls = []
        for url in url_list:
            if url not in visited_urls:
                new_urls.append(url)
                display_logger.info(f"✅ Added source url to search: {url}\n")

        return new_urls

    def search_image(
        self,
        query: str,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[ImageSearchResult]:

        # visited_urls stores the url to path mapping
        visited_urls: Dict[str, str] = {}

        if display_logger is None:
            display_logger = self.logger

        if flow_options is None:
            flow_options = {}

        retrieve_type = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_RETRIEVER_TYPE,
            default_value=self.context.settings.WEB_RETRIEVER,
            display_logger=display_logger,
        )
        retriever = create_retriever(
            retriever_type=retrieve_type,
            context=self.context,
            org=self.org,
            kb=self.kb,
            user=self.user,
        )

        flow_options[flow_option.FLOW_OPTION_IMAGE_SEARCH] = "True"

        search_results = retriever.retrieve_search_result(
            search_keywords=query,
            flow_options=flow_options,
            display_logger=display_logger,
        )

        if len(search_results) == 0:
            display_logger.info(f"No search results found for query {query}.")
            return []

        new_search_urls = self._get_new_urls(
            visited_urls=visited_urls,
            url_list=[search_result.href for search_result in search_results],
            display_logger=display_logger,
        )

        valid_extensions = {".png", ".jpg", ".jpeg"}
        save_dir = os.path.join(self.output_root, file_utils.filename_timestamp())
        os.makedirs(save_dir, exist_ok=True)
        rtn_list = []
        for url in new_search_urls:
            try:
                # Extract the file extension from the URL
                file_extension = os.path.splitext(url.split("?")[0])[1].lower()
                if file_extension not in valid_extensions:
                    display_logger.warning(
                        f"Ignoring URL without a valid image extension: {url}"
                    )
                    continue

                # Send a GET request to the URL
                response = requests.get(url, timeout=10)

                # Check if the request was successful
                response.raise_for_status()

                # Write the content to a file with a random generated uuid using uuid4 library
                file_uuid = uuid.uuid4()
                final_filename = f"image_{file_uuid}{file_extension}"
                final_filepath = os.path.join(save_dir, final_filename)
                with open(final_filepath, "wb") as f:
                    f.write(response.content)

                display_logger.info(f"Successfully downloaded {final_filepath}")
                rtn_list.append(
                    ImageSearchResult(image_url=url, image_path=final_filepath)
                )
            except requests.exceptions.RequestException as e:
                display_logger.error(f"Failed to download {url}: {e}")

        return rtn_list
