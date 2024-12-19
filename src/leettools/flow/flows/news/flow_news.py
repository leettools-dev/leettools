from typing import ClassVar, Dict, List, Optional, Type

from leettools.common.logging.event_logger import EventLogger
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import ChatQueryResultCreate, SourceItem
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import flow_option_items, iterators, steps, subflows
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.flow.schemas.article import ArticleSection, ArticleSectionPlan
from leettools.flow.utils import flow_util


def _section_plan_for_news(query: str, search_phrases: str) -> ArticleSectionPlan:
    section_plan = ArticleSectionPlan(
        title=query,
        search_query=search_phrases + " " + query,
        system_prompt_template="""
You are an expert news writer, you can write a brief news report about the topic 
using the provided context and the specified style shown in the example.
""",
        user_prompt_template=f"""
{{{{ context_presentation }}}}, please write the news report {{{{ lang_instruction }}}}
following the instructions below.

{{{{ reference_instruction }}}}
{{{{ style_instruction }}}}
{{{{ word_count_instruction }}}}
{{{{ ouput_example }}}}
                    
Here is the query: {query}                    
Here is the context: {{{{ context }}}}
""",
    )
    return section_plan


class FlowNews(AbstractFlow):
    """
    This flow will query the KB or the web for the topic and generate a paragraph
    of news about the topic using the context and specified length and style.
    """

    FLOW_TYPE: ClassVar[str] = FlowType.NEWS.value
    ARTICLE_TYPE: ClassVar[str] = ArticleType.NEWS.value
    COMPONENT_NAME: ClassVar[str] = FlowType.NEWS.value

    @classmethod
    def short_description(cls) -> str:
        return "Generating a news article from the search results."

    @classmethod
    def full_description(cls) -> str:
        return """
Specify the topic of the news post,
- Specify the number of days to search for news (right now only Google search is 
  supported for this option);
- A search agent crawls the web with the keywords in the topic and save the top 
  documents to the knowledge base;
- A summary agent summarizes the saved documents;
- A writing agent uses the summaries to generat the news item;
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

        docsource = steps.StepSearchToDocsource.run_step(exec_info=exec_info)

        display_logger.info(f"DocSource has been added to knowledge base: {kb.name}")

        iterators.Summarize.run(
            exec_info=exec_info,
            docsource=docsource,
        )

        document_summaries, all_docs, all_keywords = (
            flow_util.get_doc_summaries_for_docsource(
                docsource=docsource,
                exec_info=exec_info,
            )
        )

        sections: List[ArticleSection] = []
        accumulated_source_items: Dict[str, SourceItem] = {}
        section_plan = _section_plan_for_news(
            query=query, search_phrases=search_phrases
        )

        section = subflows.SubflowGenSection.run_subflow(
            exec_info=exec_info,
            section_plan=section_plan,
            accumulated_source_items=accumulated_source_items,
            previous_sections=sections,
        )
        sections.append(section)

        return flow_util.create_chat_result_with_sections(
            exec_info=exec_info,
            query=query,
            article_type=self.ARTICLE_TYPE,
            sections=sections,
            accumulated_source_items=accumulated_source_items,
        )
