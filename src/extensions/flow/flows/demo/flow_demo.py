from typing import ClassVar, List, Type

from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import config_utils
from leettools.core.consts.article_type import ArticleType
from leettools.core.consts.display_type import DisplayType
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
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.utils import flow_utils


class FlowDemo(AbstractFlow):
    """Flow for generating poems based on web search results."""

    FLOW_TYPE: ClassVar[str] = "DEMO"
    ARTICLE_TYPE: ClassVar[str] = ArticleType.CHAT.value
    COMPONENT_NAME: ClassVar[str] = "DEMO"

    @classmethod
    def short_description(cls) -> str:
        """Return a short description of the flow."""
        return "Generate a poem based on web search results with a specified style."

    @classmethod
    def full_description(cls) -> str:
        """Return a detailed description of the flow."""
        return """
Generate a poem based on web search results:
- Search the web for the given query
- Process and analyze the search results
- Generate a poem in the specified style using the gathered information
- Return the poem with source references
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        """Return list of dependent flow components."""
        return [
            steps.StepSearchToDocsource,
            steps.StepQueryRewrite,
            steps.StepVectorSearch,
            steps.StepInference,
            steps.StepExtendContext,
        ]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        """Return list of flow option items."""
        return AbstractFlow.direct_flow_option_items() + [
            flow_option_items.FOI_RETRIEVER(explicit=True),
            FlowOptionItem(
                name="poem_style",
                display_name="Poem Style",
                description="Style of the poem to generate (e.g., haiku, sonnet, free verse)",
                default_value="free verse",
                value_type="str",
                example_value="haiku",
                explicit=True,
                required=False,
            ),
        ]

    def execute_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: EventLogger,
    ) -> ChatQueryResultCreate:
        """Execute the poem generation flow.

        Args:
            org: Organization object
            kb: Knowledge base object
            user: User object
            chat_query_item: Chat query item containing the search query
            display_logger: Logger for displaying progress

        Returns:
            ChatQueryResultCreate object containing the generated poem and references
        """
        display_logger.debug(
            f"Execute poem generation query in KB {kb.name} for query: {chat_query_item.query_content}"
        )

        exec_info = ExecInfo(
            context=self.context,
            org=org,
            kb=kb,
            user=user,
            target_chat_query_item=chat_query_item,
            display_logger=display_logger,
        )

        query = exec_info.query
        flow_options = exec_info.flow_options

        poem_style = config_utils.get_str_option_value(
            options=flow_options,
            option_name="poem_style",
            default_value="free verse",
            display_logger=display_logger,
        )

        # Rewrite query to optimize for web search
        rewrite = steps.StepQueryRewrite.run_step(
            exec_info=exec_info,
            query_metadata=None,
        )

        keywords = rewrite.search_keywords or rewrite.rewritten_question

        # Search the web and process results
        docsource = steps.StepSearchToDocsource.run_step(
            exec_info=exec_info,
            search_keywords=keywords,
        )

        # Get relevant segments from processed content
        top_ranked_result_segments = steps.StepVectorSearch.run_step(
            exec_info=exec_info,
            query_metadata=None,
            rewritten_query=rewrite.rewritten_question,
        )

        if len(top_ranked_result_segments) == 0:
            return flow_utils.create_chat_result_for_empty_search(
                exec_info=exec_info,
                query_metadata=None,
            )

        # Extend context with relevant information
        (
            extended_context,
            context_token_count,
            source_items,
        ) = steps.StepExtendContext.run_step(
            exec_info=exec_info,
            reranked_result=top_ranked_result_segments,
            accumulated_source_items={},
        )

        display_logger.debug(
            f"Context prepared with {len(extended_context)} chars and {context_token_count} tokens"
        )

        # Add poem generation instructions to the query
        poem_prompt = f"""Generate a {poem_style} style poem based on the following information. The poem should incorporate key themes from the context while maintaining the artistic qualities of {poem_style}. Include a title for the poem.

After the poem, add a section titled 'Explanation' that describes:
1. The main themes and imagery used in the poem
2. How these elements connect to the source material
3. Why you chose specific poetic devices or structures for this {poem_style} style"""

        augmented_query = f"{poem_prompt}\n\nOriginal query: {query}"

        from openai.resources.chat.completions import ChatCompletion

        completion: ChatCompletion = steps.StepInference.run_step(
            exec_info=exec_info,
            query_metadata=None,
            rewritten_query=augmented_query,
            extended_context=extended_context,
        )

        poem_content = completion.choices[0].message.content

        # Create answer items
        caic_list = []
        caic_poem = ChatAnswerItemCreate(
            chat_id=chat_query_item.chat_id,
            query_id=chat_query_item.query_id,
            answer_content=poem_content,
            position_in_answer="1",
            answer_plan=None,
            answer_score=1.0,
            answer_source_items=source_items,
            display_type=DisplayType.HTML,
        )
        caic_list.append(caic_poem)

        return ChatQueryResultCreate(
            chat_answer_item_create_list=caic_list,
            global_answer_source_items=None,
            article_type=ArticleType.CHAT.value,
        )
