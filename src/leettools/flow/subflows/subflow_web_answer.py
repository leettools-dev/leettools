from typing import ClassVar, Dict, List, Type

import click
from pydantic import BaseModel

from leettools.chat import chat_utils
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.core.schemas.chat_query_result import SourceItem
from leettools.flow import steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.subflow import AbstractSubflow


class SubflowWebAnswer(AbstractSubflow):
    """
    A subflow to answer the question directly from the web and return answer in
    the form of a predefined pydantic model.
    """

    COMPONENT_NAME: ClassVar[str] = "web_answer"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return []

    @staticmethod
    def run_subflow(
        exec_info: ExecInfo,
        search_keywords: str,
        instruction: str,
        models: Dict[str, TypeVar_BaseModel],
        target_model_name: str,
        multi_items: bool = False,
        save_to_db: bool = True,
    ) -> List[TypeVar_BaseModel]:
        """
        The subflow queries the web and get the answer as a predefined pydantc model.

        For example, we can use the following search keywords:

        "Open AI headquarter and CEO"

        The instruction could be:

        "Please find the information about Open AI headquarter and CEO."

        The models will be a list of pydantic models that we want to use for the answer.
        Usally one model is enough, but if we have nested models, we can use multiple models.

        The target_model_name is the name of the model that we want to use for the answer.

        Args:
        - exec_info (ExecInfo): The execution information.
        - search_keywords (str): The search keywords.
        - instruction (str): The instruction for the search.
        - models (Dict[str, TypeVar_BaseModel]): The models that we want to use for the answer.
        - target_model_name (str): The name of the model that we want to use for the answer.
        - multi_items (bool): Whether to extract multiple items.
        - save_to_db (bool): Whether to save the answer to the database.

        Returns:
        - List[TypeVar_BaseModel]: The answer as a list of pydantic objects. If
          multi_items is False, the list will have only one object.
        """
        return _subflow_answer_with_web_search(
            exec_info=exec_info,
            search_keywords=search_keywords,
            instruction=instruction,
            models=models,
            target_model_name=target_model_name,
            multi_items=multi_items,
            save_to_db=save_to_db,
        )


def _subflow_answer_with_web_search(
    exec_info: ExecInfo,
    search_keywords: str,
    instruction: str,
    models: Dict[str, TypeVar_BaseModel],
    target_model_name: str,
    multi_items: bool = False,
    save_to_db: bool = True,
) -> List[TypeVar_BaseModel]:

    display_logger = exec_info.display_logger
    strategy = exec_info.strategy
    accumulated_source_items: Dict[str, SourceItem] = {}

    docsource = steps.StepSearchToDocsource.run_step(
        exec_info=exec_info,
        search_keywords=search_keywords,
    )

    if docsource is None:
        display_logger.warning("The web search step did not return any documents.")
        return []

    top_ranked_result_segments = steps.StepVectorSearch.run_step(
        exec_info=exec_info,
        query_metadata=None,
        rewritten_query=search_keywords,
    )

    if len(top_ranked_result_segments) == 0:
        display_logger.warning("No top ranked result found.")
        return []

    extended_context, context_token_count, source_items = (
        steps.StepExtendContext.run_step(
            exec_info=exec_info,
            reranked_result=top_ranked_result_segments,
            accumulated_source_items=accumulated_source_items,
        )
    )

    extracted_obj_list = steps.StepExtractInfo.run_step(
        exec_info=exec_info,
        content=extended_context,
        extraction_instructions=instruction,
        model_class=models[target_model_name],
        model_class_name=target_model_name,
        multiple_items=multi_items,
    )

    if save_to_db:
        sources = []
        for source_item in source_items.values():
            sources.append(source_item.answer_source.original_uri)

        steps.step_save_objs_list_to_db(
            exec_info=exec_info,
            objs_list=extracted_obj_list,
            models=models,
            target_model_name=target_model_name,
            key_fields=[],
            verify_fields=[],
            sources=sources,
        )

    return extracted_obj_list


@click.command()
@click.option(
    "-q",
    "--query",
    "query",
    required=True,
    help="the company name to check",
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
    "-l",
    "--log-level",
    "log_level",
    default="INFO",
    required=False,
    help="The log level to use.",
    type=click.Choice(["INFO", "DEBUG", "ERROR", "WARNING"]),
)
def get_answer_from_web(
    query: str,
    org_name: str,
    kb_name: str,
    username: str,
    log_level: str,
) -> None:

    EventLogger.set_global_default_level(log_level.upper())

    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_report"

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org_name,
        kb_name=kb_name,
        username=username,
        strategy_name=None,
        flow_options={},
        display_logger=None,
    )

    class CompanyInfo(BaseModel):
        name: str
        address: str
        ceo: str

    objects = _subflow_answer_with_web_search(
        exec_info=exec_info,
        search_keywords=query,
        instruction="Please find the headquarter city and name of CEO for the specified company.",
        models={"company_info": CompanyInfo},
        target_model_name="company_info",
        multi_items=False,
    )

    for obj in objects:
        print(obj.model_dump())


if __name__ == "__main__":
    get_answer_from_web()
