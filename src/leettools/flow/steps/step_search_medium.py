import json
import requests

from datetime import datetime, timezone

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import ClassVar, Dict, List, Optional, Type

from leettools.common import exceptions
from leettools.common.logging import EventLogger, logger
from leettools.flow import flow_option_items
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.schemas.medium_article import MediumArticle
from leettools.flow.step import AbstractStep
from leettools.web.web_searcher import WebSearcher
from leettools.web.web_scraper import WebScraper

ID_ATTR = "id"
SNIPPET_ATTR = "body"


class StepSearchMedium(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "search_medium"

    @classmethod
    def short_description(cls) -> str:
        return "Search the Medium.com to get related articles and return their ids."

    @classmethod
    def full_description(cls) -> str:
        return """Create a list of article ids with web search from Medium.com. """

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [WebSearcher]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return AbstractStep.get_flow_option_items() + [
            flow_option_items.FOI_RETRIEVER(explicit=True),
            flow_option_items.FLOW_OPTION_SEARCH_ITERATION(explicit=True),
            flow_option_items.FOI_DAYS_LIMIT(explicit=True),
            flow_option_items.FOI_SEARCH_MAX_RESULTS(explicit=True),
        ]

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        search_keywords: Optional[str] = None,
    ) -> List[MediumArticle]:
        """
        Create a list of Medium.com article ids with web search.

        Args:
        - exec_info: Execution information
        - search_keywords: The search keywords. If not provided, the original query
          from the chat_query_item will be used.
        - schedule_config: The schedule config for the document source. If not provided,
            the default schedule config will be used.

        Returns:
        -  The list of article ids from Medium.com.
        """

        display_logger = exec_info.display_logger
        if display_logger is None:
            display_logger = logger()

        if exec_info.target_chat_query_item is None:
            raise exceptions.UnexpectedCaseException(
                "The chat query item is not provided."
            )

        if search_keywords is None:
            search_keywords = exec_info.target_chat_query_item.query_content

        display_logger.info("[Status]Start the medium search pipeline ...")
        medium_articles = _run_medium_search_pipeline(exec_info, search_keywords)
        display_logger.info(
            f"Successfully find {len(medium_articles)} "
            "Medium.com articles from search."
        )
        return medium_articles


def _run_medium_search_pipeline(
    exec_info: ExecInfo, search_keywords: str
) -> List[MediumArticle]:
    context = exec_info.context
    org = exec_info.org
    kb = exec_info.kb
    user = exec_info.user
    flow_options = exec_info.target_chat_query_item.chat_query_options.flow_options
    display_logger = exec_info.display_logger
    if display_logger is None:
        display_logger = logger()

    # make sure the target site is medium
    flow_options[flow_option_items.FLOW_OPTION_TARGET_SITE] = "medium.com"

    searcher = WebSearcher(context=context)
    search_results = searcher.simple_search(
        context=context,
        org=org,
        kb=kb,
        user=user,
        search_keywords=search_keywords,
        flow_options=flow_options,
    )
    post_ids_from_google = []
    for search_result in search_results:
        post_id = search_result.href.split("-")[-1]
        if post_id.isalnum():
            post_ids_from_google.append(
                {ID_ATTR: post_id, SNIPPET_ATTR: search_result.snippet}
            )

    scraper = WebScraper(context=context)
    partial_extract = partial(_scrape_and_parse_article, scraper, display_logger)
    with ThreadPoolExecutor(max_workers=2) as executor:
        rtn_articles = list(executor.map(partial_extract, post_ids_from_google))
        articles = [article for article in rtn_articles if article is not None]
    return articles


def _scrape_and_parse_article(
    scraper: WebScraper, display_logger: EventLogger, article_json: Dict[str, any]
) -> Optional[MediumArticle]:
    article_id = article_json[ID_ATTR]
    article_body = article_json[SNIPPET_ATTR]
    # get the whole content of the page the article content
    article_content = _get_page_content(f"https://medium.com/_/api/posts/{article_id}")
    if article_content is None:
        display_logger.error(f"Failed to get article {article_id}")
        return None
    return _parse_article(article_content, article_body)


def _parse_article(article_content: str, article_body: str) -> Optional[MediumArticle]:
    start_index = article_content.find("</x>")
    if start_index == -1:
        return None

    json_str = article_content[start_index + 4 :]
    try:
        article = json.loads(json_str)
        if "success" not in article or not article["success"]:
            return None

        id = article["payload"]["value"]["id"]
        author_id = article["payload"]["value"]["creatorId"]
        title = article["payload"]["value"]["title"]
        total_clap_count = article["payload"]["value"]["virtuals"]["totalClapCount"]
        section_count = article["payload"]["value"]["virtuals"]["sectionCount"]

        # 1. Extract the subtitle
        subtitle = article["payload"]["value"]["content"].get("subtitle", "")

        # 2. Extract the list of paragraphs
        paragraphs = article["payload"]["value"]["content"]["bodyModel"]["paragraphs"]

        # 3. Collect the text from each paragraph
        paragraph_texts = [p["text"] for p in paragraphs]

        # 4. Combine everything into a single string
        #    For readability, we join using "\n\n" (double newline).
        combined_content = subtitle + "\n\n" + "\n\n".join(paragraph_texts)

        tags = article["payload"]["value"]["virtuals"]["tags"]
        tag_list = [tag["slug"] for tag in tags]
        url = f"https://medium.com/p/{id}"

        # 6. get created and updated time
        created_at_ms = article["payload"]["value"]["createdAt"]
        updated_at_ms = article["payload"]["value"]["updatedAt"]
        created_at_dt = datetime.fromtimestamp(created_at_ms / 1000, timezone.utc)
        updated_at_dt = datetime.fromtimestamp(updated_at_ms / 1000, timezone.utc)
        created_at_str = created_at_dt.strftime("%Y-%m-%d")
        updated_at_str = updated_at_dt.strftime("%Y-%m-%d")

        return MediumArticle(
            id=id,
            author_id=author_id,
            title=title,
            summary=combined_content,
            body=article_body,
            claps=total_clap_count,
            responses=section_count,
            tags=tag_list,
            url=url,
            created_at=created_at_str,
            updated_at=updated_at_str,
        )
    except json.JSONDecodeError:
        return None


def _get_page_content(url: str) -> Optional[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/92.0.4515.159 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # raise an HTTPError for bad responses
        return response.text
    except requests.RequestException as e:
        return None
