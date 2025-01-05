from typing import ClassVar, Dict, List, Optional, Type

from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import template_eval
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import ChatQueryResultCreate, SourceItem
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.prompt import (
    PromptBase,
    PromptCategory,
    PromptType,
)
from leettools.flow import flow_option_items, iterators, steps, subflows
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.flow.schemas.article import ArticleSection, ArticleSectionPlan
from leettools.flow.utils import flow_utils


def _section_plan_for_posts(query: str, search_phrases: str) -> ArticleSectionPlan:

    user_prompt_template = FlowPosts.used_prompt_templates()[
        FlowPosts.COMPONENT_NAME
    ].prompt_template

    # other variables are instantiated in the gen-section step
    # using variables defined in the flow_options.
    user_prompt_template = template_eval.render_template(
        template_str=user_prompt_template,
        variables={"query": query},
        allow_partial=True,
    )

    section_plan = ArticleSectionPlan(
        title=query,
        search_query=search_phrases + " " + query,
        system_prompt_template="""
    You are an expert news writer, you can write a brief news report about the topic 
    using the provided context and the specified style shown in the example.
    """,
        user_prompt_template=user_prompt_template,
    )
    return section_plan


class FlowPosts(AbstractFlow):
    """
    This flow will query the KB or the web for the topic and generate a post
    about the topic using the context and specified length and style.
    """

    FLOW_TYPE: ClassVar[str] = FlowType.NEWS.value
    ARTICLE_TYPE: ClassVar[str] = ArticleType.NEWS.value
    COMPONENT_NAME: ClassVar[str] = FlowType.NEWS.value

    @classmethod
    def short_description(cls) -> str:
        return "Generating a post from the search results."

    @classmethod
    def full_description(cls) -> str:
        return """
Specify the topic of the post,
- Specify the number of days to search for the content (right now only Google search is 
  supported for this option);
- Crawl the web with the keywords in the topic and save the top documents to the KB;
- Summarize the saved documents;
- Use the summaries to generat the post;
- You can specify the output language, the number of words, and article style.
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [
            steps.StepGenSearchPhrases,
            steps.StepSearchToDocsource,
            iterators.Summarize,
            subflows.SubflowGenSection,
        ]

    @classmethod
    def used_prompt_templates(cls) -> Dict[str, PromptBase]:
        # the difficult part of using a generic template evaluation step is that
        # the variables are instantiated at varies steps in the flow
        news_prompt_template = """
{{ context_presentation }}, please write the report {{ lang_instruction }}
following the instructions below.

{{ reference_instruction }}
{{ style_instruction }}
{{ word_count_instruction }}
{{ ouput_example }}
                    
Here is the query: {{ query }}
Here is the context: {{ context }}
"""
        return {
            cls.COMPONENT_NAME: PromptBase(
                prompt_category=PromptCategory.SUMMARIZATION,
                prompt_type=PromptType.USER,
                prompt_template=news_prompt_template,
                prompt_variables={
                    "context_presentation": "The context presentation.",
                    "lang_instruction": "The instruction for the language.",
                    "reference_instruction": "The instruction for the reference.",
                    "style_instruction": "The instruction for the style.",
                    "word_count_instruction": "The instruction for the word count.",
                    "ouput_example": "The output example.",
                    "query": "The query.",
                    "context": "The context.",
                },
            )
        }

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        days_limit = flow_option_items.FOI_DAYS_LIMIT(explicit=True)
        days_limit.default_value = "3"
        days_limit.example_value = "3"

        word_count = flow_option_items.FOI_WORD_COUNT(explicit=True)
        word_count.default_value = "280"
        word_count.example_value = "280"

        reference_style = flow_option_items.FOI_REFERENCE_STYLE()
        reference_style.default_value = "news"
        reference_style.example_value = "news"
        reference_style.description = "Do not show reference in the text."

        return AbstractFlow.get_flow_option_items() + [
            days_limit,
            word_count,
            reference_style,
        ]

    def execute_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: Optional[EventLogger] = None,
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

        # flow starts here
        search_phrases = steps.StepGenSearchPhrases.run_step(exec_info=exec_info)

        docsource = steps.StepSearchToDocsource.run_step(
            exec_info=exec_info,
            search_keywords=search_phrases,
        )

        display_logger.info(f"DocSource has been added to knowledge base: {kb.name}")

        # TODO: right now the document summarization is actually no longger used
        # in the post generation. The gen-section step will query the KB using
        # the rewritten query and generate the news article.
        iterators.Summarize.run(
            exec_info=exec_info,
            docsource=docsource,
        )

        document_summaries, all_docs, all_keywords = (
            flow_utils.get_doc_summaries_for_docsource(
                docsource=docsource,
                exec_info=exec_info,
            )
        )

        sections: List[ArticleSection] = []
        accumulated_source_items: Dict[str, SourceItem] = {}
        section_plan = _section_plan_for_posts(
            query=query, search_phrases=search_phrases
        )
        section = subflows.SubflowGenSection.run_subflow(
            exec_info=exec_info,
            section_plan=section_plan,
            accumulated_source_items=accumulated_source_items,
            previous_sections=sections,
        )
        sections.append(section)

        return flow_utils.create_chat_result_with_sections(
            exec_info=exec_info,
            query=query,
            article_type=self.ARTICLE_TYPE,
            sections=sections,
            accumulated_source_items=accumulated_source_items,
        )
