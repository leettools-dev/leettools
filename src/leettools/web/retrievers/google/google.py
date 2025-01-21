import json
import os
import urllib.parse
from typing import Any, Dict, List, Optional

import requests

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import file_utils
from leettools.common.utils.file_utils import redact_api_key
from leettools.context_manager import Context
from leettools.core.consts import flow_option
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.user.user_settings_helper import get_value_from_settings
from leettools.settings import SystemSettings
from leettools.web import search_utils
from leettools.web.retrievers.retriever import AbstractRetriever
from leettools.web.schemas.search_result import SearchResult


class GoogleSearch(AbstractRetriever):
    """
    Google Search Retriever
    """

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        """
        Initializes the Google Search object
        Args:
            query:
        """
        super().__init__(context, org, kb, user)
        self.api_key = self._get_api_key()
        self.cx_key = self._get_cx_key(cx_name="GOOGLE_CX_KEY")
        self.google_url_base = context.settings.SEARCH_API_URL

    def retrieve_search_result(
        self,
        search_keywords: str,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[SearchResult]:
        """
        Useful for general internet search queries using the Google API.
        Google API only allow return 10 results each time, so we need to
        set the start parameter to get more results.
        """
        # we can specify a different logger to show some items in the UI
        if display_logger is None:
            display_logger = self.logger

        if flow_options is None:
            flow_options = {}

        return self._retrieve(search_keywords, flow_options, display_logger)

    def _retrieve(
        self,
        query: str,
        flow_options: Dict[str, Any],
        display_logger: EventLogger,
    ) -> List[SearchResult]:

        from leettools.common.utils import config_utils
        from leettools.core.consts.flow_option import (
            FLOW_OPTION_EXCLUDED_SITES,
            FLOW_OPTION_IMAGE_SEARCH,
            FLOW_OPTION_SEARCH_ITERATION,
            FLOW_OPTION_TARGET_SITE,
        )

        display_logger.info(f"Google search with query: {query}...")

        days_limit, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=self.context.settings,
            display_logger=display_logger,
        )

        if days_limit == 0:
            date_restrict = ""
        else:
            date_restrict = f"&dateRestrict=d{days_limit}"

        target_site = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_TARGET_SITE,
            default_value=None,
            display_logger=display_logger,
        )
        if target_site is not None:
            target_site_filter = f"&siteSearch={target_site}&siteSearchFilter=i"
        else:
            target_site_filter = ""

        image_search = config_utils.get_bool_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_IMAGE_SEARCH,
            default_value=False,
            display_logger=display_logger,
        )
        if image_search:
            image_search_flag = "&searchType=image"
        else:
            image_search_flag = ""

        excluded_sites_value = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_EXCLUDED_SITES,
            default_value=None,
            display_logger=display_logger,
        )

        excluded_sites_value = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_EXCLUDED_SITES,
            default_value=None,
            display_logger=display_logger,
        )

        if excluded_sites_value is None:
            excluded_sites = []
        else:
            if isinstance(excluded_sites_value, list):
                excluded_sites = excluded_sites_value
            elif isinstance(excluded_sites_value, str):
                excluded_sites = excluded_sites_value.split(",")
            else:
                raise exceptions.ConfigValueException(
                    config_item=f"flow_options.{FLOW_OPTION_EXCLUDED_SITES}",
                    value=excluded_sites_value,
                )

        max_iteration = config_utils.get_int_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_SEARCH_ITERATION,
            default_value=3,
            display_logger=display_logger,
        )

        if max_iteration == 0:
            display_logger.warning(
                f"Max iteration is set to 0, which means no search will be performed."
                f"Setting it to default value 3."
            )
            max_iteration = 3

        start = 1
        iteration = 0
        search_results = []
        last_iteration_filled = True

        escaped_query = urllib.parse.quote(query)
        url_base = f"{self.google_url_base}?key={self.api_key}&cx={self.cx_key}&q={escaped_query}"
        redacted_url_base = (
            f"{self.google_url_base}?key={redact_api_key(self.api_key)}"
            f"&cx={redact_api_key(self.cx_key)}&q={escaped_query}"
        )
        display_logger.debug(f"Google API request: {redacted_url_base}")

        while (
            len(search_results) < max_results
            and iteration < max_iteration
            and last_iteration_filled
        ):
            iteration += 1

            # TODO: we should be able to allow the user to set the parameters
            # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
            # tempalte
            # "https://www.googleapis.com/customsearch/v1?q={searchTerms}
            #   &num={count?}&start={startIndex?}&lr={language?}&safe={safe?}
            #   &cx={cx?}&sort={sort?}&filter={filter?}&gl={gl?}&cr={cr?}
            #   &googlehost={googleHost?}&c2coff={disableCnTwTranslation?}
            #   &hq={hq?}&hl={hl?}&siteSearch={siteSearch?}
            #   &siteSearchFilter={siteSearchFilter?}
            #   &exactTerms={exactTerms?}
            #   &excludeTerms={excludeTerms?}
            #   &linkSite={linkSite?}
            #   &orTerms={orTerms?}&dateRestrict={dateRestrict?}
            #   &lowRange={lowRange?}&highRange={highRange?}
            #   &searchType={searchType}
            #   &fileType={fileType?}
            #   &rights={rights?}&imgSize={imgSize?}
            #   &imgType={imgType?}&imgColorType={imgColorType?}
            #   &imgDominantColor={imgDominantColor?}&alt=json"
            url_paras = (
                f"&safe=active"
                f"&start={start}"
                f"{date_restrict}"
                f"{target_site_filter}"
                f"{image_search_flag}"
            )

            url = f"{url_base}{url_paras}"
            redacted_url = f"{redacted_url_base}{url_paras}"

            results = self._process_url(url, redacted_url, display_logger)
            if results is None:
                display_logger.warning(
                    f"[Iteration{iteration}] "
                    f"Failed Google API request for {redacted_url}."
                )
                return search_results

            if len(results) < 10:
                last_iteration_filled = False

            # Normalizing results to match the format of the other search APIs

            # One possible optimization is that if the number of results in the current
            # iteration is smaller than 10, we can stop the search since google
            # will not have more results.
            for result in results:
                href = result.get("link", None)
                if href is None or href == "":
                    display_logger.warning(f"Search result link missing: {result}")
                    continue
                # skip youtube results
                if "youtube.com" in href or "youtu.be" in href:
                    display_logger.debug(f"Youtube search result link skipped: {href}")
                    continue

                base_domain = file_utils.get_base_domain(href)
                if excluded_sites is not None and base_domain in excluded_sites:
                    display_logger.debug(f"{href} in excluded site: {base_domain}")
                    continue

                display_logger.debug(f"Search result link: {href}")
                search_result = SearchResult(
                    href=href,
                    title=result.get("title", None),
                    snippet=result.get("snippet", None),
                )
                search_results.append(search_result)
                if len(search_results) >= max_results:
                    break
            start += 10

        return search_results

    def _process_url(
        self, url: str, redacted_url: str, display_logger: EventLogger
    ) -> List[SearchResult]:
        """
        Process the URL to remove the tracking information
        """
        resp = requests.get(url)

        if resp is None:
            display_logger.warning(
                f"No response from Google API for request {redacted_url}."
            )
            return None

        display_logger.debug(f"Google API response: {resp.text}")

        search_results_dict = None
        try:
            search_results_dict = json.loads(resp.text)
            if search_results_dict is not None:
                if "error" in search_results_dict:
                    display_logger.warning(
                        f"Error in Google API response {search_results_dict['error']}"
                    )
                    return None
                if "searchInformation" in search_results_dict:
                    total_results = search_results_dict["searchInformation"].get(
                        "totalResults", 0
                    )
                    display_logger.debug(f"Total search results: {total_results}")
                    if total_results == 0:
                        display_logger.warning("Search returned 0 results.")
                        return None
        except Exception as e:
            display_logger.error(f"Error parsing Google API response: {e}")
            display_logger.error(f"Google API request url: {redacted_url}")
            display_logger.error(f"Google API response: {resp.text}")
            return None
        if search_results_dict is None or len(search_results_dict) == 0:
            display_logger.warning(
                f"search_results_dict is None or empty, which should not happen."
            )
            return None

        results = search_results_dict.get("items", [])
        if results is None or len(results) == 0:
            display_logger.warning(f"No 'items' field in resp.text.")
            return None
        return results

    def _get_api_key(self) -> str:
        try:
            if self.user is not None:
                user = User.get_admin_user()
            else:
                user = self.user

            user_settings = (
                self.context.get_user_settings_store().get_settings_for_user(user)
            )
            # the get_value_from_settings will fall back to admin_user settings
            # if the user settings has no GOOGLE_API_KEY
            api_key = get_value_from_settings(
                context=self.context,
                user_settings=user_settings,
                default_env="GOOGLE_API_KEY",
                first_key="GOOGLE_API_KEY",
                second_key=None,
                allow_empty=False,
            )
        except Exception as e:
            self.logger.debug(
                "Failed to get Google API key. Maybe using a proxy, set the dummp key "
                "instead. If possible, please set the EDS_GOOGLE_API_KEY environment variable. "
                "You can get a key at https://developers.google.com/custom-search/v1/overview:\n"
                f"{e}"
            )
            api_key = "dummy_google_api_key"
        return api_key

    def _get_cx_key(self, cx_name: str) -> str:
        try:
            if self.user is not None:
                user = User.get_admin_user()
            else:
                user = self.user
            user_settings = (
                self.context.get_user_settings_store().get_settings_for_user(user)
            )
            api_key = get_value_from_settings(
                context=self.context,
                user_settings=user_settings,
                default_env=cx_name,
                first_key=cx_name,
                second_key=None,
                allow_empty=False,
            )
        except:
            self.logger.debug(
                f"Failed to get Google CX key {cx_name}. Maybe using a proxy, set the "
                f"dummy key instead. If possible, please set the {cx_name} environment "
                "variable. This should be your custom search engine ID. You can get a "
                "key at https://cse.google.com/cse"
            )
            api_key = "dummy_google_cx_key"
        return api_key
