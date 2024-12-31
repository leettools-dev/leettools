from typing import ClassVar, Dict, List, Type

import click

from leettools.chat import chat_utils
from leettools.common.exceptions import EntityNotFoundException
from leettools.common.logging.event_logger import EventLogger
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_result import ChatQueryResultCreate, SourceItem
from leettools.flow import flow_option_items, steps, subflows
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.flow.schemas.article import ArticleSection, ArticleSectionPlan, TopicSpec
from leettools.flow.subflow import AbstractSubflow
from leettools.flow.utils import flow_utils


class SubflowGenEssay(AbstractSubflow):
    """
    Subflow to generate an essay based on the article type and the document summaries.
    """

    COMPONENT_NAME: ClassVar[str] = "gen_essay"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [
            steps.StepIntention,
            steps.StepPlanTopic,
            steps.StepGenIntro,
            subflows.SubflowGenSection,
        ]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return [flow_option_items.FOI_REFERENCE_STYLE()]

    @staticmethod
    def run_subflow(
        exec_info: ExecInfo,
        article_type: str,
        document_summaries: str,
    ) -> ChatQueryResultCreate:
        """
        We organize these steps together so that we can generate a report for a single
        docsource as illustrated by the CLI.

        Args:
        - exec_info: the execution information
        - article_type: the type of the article
        - document_summaries: the document summaries

        Returns:
        - the chat query result create
        """
        display_logger = exec_info.display_logger
        query = exec_info.target_chat_query_item.query_content

        query_metadata = steps.StepIntention.run_step(exec_info=exec_info)

        intro_section = steps.StepGenIntro.run_step(
            exec_info=exec_info,
            content=document_summaries,
            query_metadata=query_metadata,
        )

        topic_list = steps.StepPlanTopic.run_step(
            exec_info=exec_info,
            content=document_summaries,
            query_metadata=query_metadata,
        )

        sections: List[ArticleSection] = [intro_section]

        # the key is segment_uuid
        accumulated_source_items: Dict[str, SourceItem] = {}
        for topic in topic_list.topics:
            display_logger.info(f"Topic: {topic}")

            section_plan = _section_plan_for_research(topic=topic, query=query)

            section = subflows.SubflowGenSection.run_subflow(
                exec_info=exec_info,
                section_plan=section_plan,
                accumulated_source_items=accumulated_source_items,
                previous_sections=sections,
            )
            display_logger.debug(
                f"Section created, the source_items now have {len(accumulated_source_items)} items."
            )
            sections.append(section)

        return flow_utils.create_chat_result_with_sections(
            exec_info=exec_info,
            query=query,
            article_type=article_type,
            sections=sections,
            accumulated_source_items=accumulated_source_items,
        )


def _section_plan_for_research(topic: TopicSpec, query: str):
    """
    Generate a section plan for research based on the topic.

    In the prompts, there are several types of variables we can use:
    - {{{{ lang_instruction }}}} : these will be replaced at runtime using the
      lang_instruction function call in the prompt_util module, since the language
      can be only determined at runtime. Same with 'context'
    - {{{{ reference_instruction }}}} : although these are fixed instructions, we use
      a util function to generate them in the prompt_util module.
    - {topic.title} : will be replaced with the topic.title variable in this function.
    Therefore the main work here is to set up the role in the system prompt and the
    concatenation of different instructions in the user prompt.

    Check promt_util.py for more details on which variables and instructions are available.
    """

    # We tried to add this instruction to the user prompt, but it is not very useful
    #
    # Do not repeat the statements already made in the previous sections.
    # Here are the previous sections:
    # {{{{ previous_sections }}}}

    section_plan = ArticleSectionPlan(
        title=topic.title,
        search_query=query + " " + topic.title,
        system_prompt_template="""
You are an expert research writer, you can write a detailed section about the topic 
using the provided context and the specified style shown in the example.
""",
        user_prompt_template=f"""
{{{{ context_presentation }}}} please write the section {{{{ lang_instruction }}}} 
following the instructions below. 

{topic.prompt}
{{{{ reference_instruction }}}}
Do not include the topic title in the section answer.
Do not write a section summary such as "In this section, ..." or "In conclusion, ...".
{{{{ strict_context_instruction }}}}

Here is the query: {query}
Here is the topic: {topic.title}
Here is the context:\n{{{{ context }}}}
""",
    )
    return section_plan


@click.command()
@click.option(
    "-q",
    "--query",
    "query",
    required=True,
    help="the question to ask",
)
@click.option(
    "-s",
    "--strategy",
    "strategy_name",
    default=None,
    required=False,
    help="The strategy to use.",
)
@click.option(
    "-g",
    "--org",
    "org_name",
    default=None,
    required=False,
    help="The org to add the documents to.",
)
@click.option(
    "-k",
    "--kb",
    "kb_name",
    default=None,
    required=False,
    help="The knowledgebase to add the documents to.",
)
@click.option(
    "-u",
    "--user",
    "username",
    default=None,
    required=False,
    help="The user to use, default the admin user.",
)
@click.option(
    "-d",
    "--docsource_uuid",
    "docsource_uuid",
    required=True,
    help="The docsource uuid to report on.",
)
@click.option(
    "-l",
    "--log-level",
    "log_level",
    default="INFO",
    required=False,
    help="The log level to use.",
    type=click.Choice(["INFO", "DEBUG", "ERROR", "WARNING"]),
)
def report_for_docsource(
    query: str,
    strategy_name: str,
    org_name: str,
    kb_name: str,
    username: str,
    docsource_uuid: str,
    log_level: str,
) -> None:

    EventLogger.set_global_default_level(log_level.upper())

    from leettools.context_manager import ContextManager

    flow_type = FlowType.DIGEST
    article_type = ArticleType.RESEARCH

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = flow_type

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org_name,
        kb_name=kb_name,
        username=username,
        strategy_name=strategy_name,
        flow_type=flow_type,
        flow_options={},
        display_logger=None,
    )

    docsource = (
        context.get_repo_manager()
        .get_docsource_store()
        .get_docsource(
            org=exec_info.org, kb=exec_info.kb, docsource_uuid=docsource_uuid
        )
    )

    if docsource is None:
        raise EntityNotFoundException(
            entity_name=docsource_uuid, entity_type="DocSource"
        )

    document_summaries, all_docs, all_keywords = (
        flow_utils.get_doc_summaries_for_docsource(
            docsource=docsource,
            exec_info=exec_info,
        )
    )

    chat_query_result_create = SubflowGenEssay.run_subflow(
        exec_info=exec_info,
        article_type=article_type,
        document_summaries=document_summaries,
    )

    print("****************\nThe final report\n****************\n")
    print(chat_query_result_create.chat_answer_item_create_list[0].answer_content)


if __name__ == "__main__":
    report_for_docsource()
