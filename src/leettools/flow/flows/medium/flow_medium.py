from datetime import datetime
from typing import ClassVar, List

import click

from leettools.common.logging import EventLogger
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import (
    ChatAnswerItemCreate,
    ChatQueryResultCreate,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import flow_option_items, steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.flow.flows.medium.prompts import QUERY_PROMPT, SUMMARY_PROMPT
from leettools.flow.schemas.medium_article import MediumArticle

MAX_ARTICLE_NUMBER = 10
ARTICEL_LENGTH = 2000


class FlowMedium(AbstractFlow):
    FLOW_TYPE: ClassVar[str] = FlowType.MEDIUM.value
    ARTICLE_TYPE: ClassVar[str] = ArticleType.RESEARCH.value
    COMPONENT_NAME: ClassVar[str] = FlowType.MEDIUM.value

    @classmethod
    def short_description(cls) -> str:
        return (
            "Give writing suggestions about the inputed"
            " topic by analyzing related popular articles on Medium.com."
        )

    @classmethod
    def full_description(cls) -> str:
        return """
Give writing suggestions about the inputed topic:
- Perform the search with retriever on Medium.com: Sort the results by the number of
claps and pick the top 10 articles as the learning target.
- Using DeepSeek R1 model to analyze the top articles and give writing suggestions.
"""

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return AbstractFlow.direct_flow_option_items() + [
            flow_option_items.FOI_RETRIEVER(explicit=True, required=True),
            flow_option_items.FOI_DAYS_LIMIT(explicit=True, required=True),
            flow_option_items.FOI_SEARCH_MAX_ITERATION(explicit=True, required=True),
            flow_option_items.FOI_SEARCH_MAX_RESULTS(explicit=True, required=True),
        ]

    def execute_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: EventLogger,
    ) -> ChatQueryResultCreate:

        exec_info = ExecInfo(
            context=self.context,
            org=org,
            kb=kb,
            user=user,
            target_chat_query_item=chat_query_item,
            display_logger=display_logger,
        )

        query = exec_info.query
        article_list = steps.StepSearchMedium.run_step(exec_info, query)
        if not article_list:
            answer_content = "No articles found."
        else:
            article_list = sorted(article_list, key=lambda x: x.claps, reverse=True)
            user_prompt = self._generate_prompt(query, article_list, display_logger)
            api_caller = exec_info.get_inference_caller()
            answer_content, _ = api_caller.run_inference_call(
                system_prompt=(
                    "You are an assistant that creates structured"
                    " writing suggestions for Medium articles in Markdown format"
                ),
                user_prompt=user_prompt,
                need_json=False,
                call_target="get_medium_topic_suggestion",
            )
            # create a content that containts all the articles, format:
            # id: title - url
            answer_content = f"Blog Topic Suggestion for {query}:\n\n" + answer_content
            answer_content += "\n\nReferences:\n"
            for idx, article in enumerate(article_list, start=1):
                if idx > MAX_ARTICLE_NUMBER:
                    break
                answer_content += f"Article {idx}: {article.title} - {article.url}\n"

        answer_source_items = None
        chat_answer_item_create = ChatAnswerItemCreate(
            chat_id=chat_query_item.chat_id,
            query_id=chat_query_item.query_id,
            answer_content=answer_content,
            answer_plan=None,
            answer_score=1.0,
            answer_source_items=answer_source_items,
        )

        return ChatQueryResultCreate(
            chat_answer_item_create_list=[chat_answer_item_create]
        )

    def _generate_prompt(
        self,
        search_query: str,
        articles: List[MediumArticle],
        display_logger: EventLogger,
    ) -> str:
        """
        Generates a prompt for the OpenAI API based on the collected Task data.

        :return: A formatted prompt string.
        """
        # Start constructing the collected data section
        collected_data = ""
        if articles:
            collected_data += f"\n\n"
            for idx, article in enumerate(articles, start=1):
                if idx > MAX_ARTICLE_NUMBER:
                    display_logger.debug(
                        f"Collected {idx} articles for summary, each article is {ARTICEL_LENGTH} characters long"
                    )
                    break
                collected_data += f"- ** Article {idx}:**\n"
                collected_data += f"  - **Title:** {article.title}\n"
                collected_data += f"  - **Summary:**\n<summary> {article.summary[:ARTICEL_LENGTH]}...\n</summary>\n"
                collected_data += f"  - **URL:** {article.url}\n"
                tags = ", ".join(article.tags) if article.tags else "N/A"
                collected_data += f"  - **Tags/Topics:** {tags}  _(Comma-separated)_\n"
                collected_data += f"  - **Claps Count:** {article.claps}\n"
                collected_data += f"  - **Created Date:** {article.created_at}  _(Format: YYYY-MM-DD)_\n"
                collected_data += f"  - **Updated Date:** {article.updated_at}  _(Format: YYYY-MM-DD)_\n"
                collected_data += "\n\n\n"
        else:
            collected_data += "  - No articles available.\n"

        return SUMMARY_PROMPT.format(
            topic=search_query,
            search_query=search_query,
            collected_data=collected_data,
        )


@click.command()
@click.option("--search_keywords", "-s", default="RAG", help="The search keywords.")
def main(search_keywords: str):
    from leettools.cli.cli_utils import setup_org_kb_user
    from leettools.common.logging import EventLogger
    from leettools.context_manager import ContextManager
    from leettools.core.schemas.chat_query_item import ChatQueryItem
    from leettools.core.schemas.chat_query_options import ChatQueryOptions
    from leettools.flow.flow_option_items import (
        FLOW_OPTION_DAYS_LIMIT,
        FLOW_OPTION_SEARCH_ITERATION,
        FLOW_OPTION_SEARCH_MAX_RESULTS,
    )

    EventLogger.set_global_default_level("DEBUG")

    context = ContextManager().get_context()
    org, kb, user = setup_org_kb_user(
        context=context,
        org_name=None,
        kb_name=None,
        username=None,
    )

    flow_option = {
        FLOW_OPTION_SEARCH_ITERATION: 5,
        FLOW_OPTION_SEARCH_MAX_RESULTS: 50,
        FLOW_OPTION_DAYS_LIMIT: 180,
    }

    target_chat_query_item = ChatQueryItem(
        query_content=search_keywords,
        query_id="test",
        chat_id="test",
        created_at=datetime.now(),
        chat_query_options=ChatQueryOptions(flow_options=flow_option),
    )

    flow = FlowMedium(context=context)
    result: ChatQueryResultCreate = flow.execute_query(
        org=org,
        kb=kb,
        user=user,
        chat_query_item=target_chat_query_item,
        display_logger=flow.display_logger,
    )
    click.echo(result.chat_answer_item_create_list[0].answer_content)


if __name__ == "__main__":
    main()
