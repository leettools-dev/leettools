import json
import os
from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils.template_eval import render_template
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_display_settings import (
    StrategySectionName,
)
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.eds.api_caller.api_caller_base import APICallerBase

_script_dir = os.path.dirname(os.path.abspath(__file__))


class LLMCliTool(APICallerBase):
    def __init__(
        self,
        context: Context,
        user: User,
        section: StrategySection,
        event_logger: Optional[EventLogger] = None,
    ):
        self.setup_with_strategy(context, user, section, _script_dir, event_logger)


def inference_func(
    query: str,
    input_text: Optional[str] = None,
    user_prompt_file: Optional[str] = None,
    system_prompt: Optional[str] = None,
    need_json: Optional[bool] = False,
    username: Optional[str] = None,
    strategy_name: Optional[str] = None,
) -> str:
    """
    Command line interface for model inference, to read the input text file to
    interact with OpenAI's completion model to generate the output.

    Args:
    - query: The query to run.
    - input_text: The text file to read as the context.
    - user_prompt_file: User prompt template to use, the query and the context will be used as the variables.
    - system_prompt: System prompt to use.
    - need_json: Whether to output the result as JSON.
    - username: The user to use, default the admin user.
    - strategy_name: The strategy to use.

    Returns:
    - The response from the model.
    """
    context = ContextManager().get_context()  # type: Context
    display_logger = logger()
    repo_manager = context.get_repo_manager()

    strategy_store = context.get_strategy_store()
    user_store = context.get_user_store()

    if username is None:
        user = User.get_admin_user()
    else:
        user = user_store.get_user_by_name(username)
        if user is None:
            raise exceptions.EntityNotFoundException(
                entity_name=username, entity_type="User"
            )

    if strategy_name is not None:
        strategy = strategy_store.get_active_strategy_by_name(strategy_name, user)
    else:
        strategy = strategy_store.get_default_strategy()

    inference_section = strategy.strategy_sections[StrategySectionName.INFERENCE]

    if inference_section is None:
        raise exceptions.UnexpectedCaseException("Inference section is None.")

    display_logger.info(f"[Status]Running inference for query {query}.")

    llm_cli_tool = LLMCliTool(context, user, inference_section, display_logger)

    if user_prompt_file is not None:
        with open(user_prompt_file, "r", encoding="utf-8") as file:
            user_prompt_template = file.read()
    else:
        user_prompt_template = "{{ query }}\n{{ content }}"

    if input_text is None:
        content = ""
    else:
        if os.path.isabs(input_text):
            filename = input_text
        else:
            # If it's not an absolute path, get the current working directory
            current_dir = os.getcwd()
            # Join the current working directory with the filename
            filename = os.path.join(current_dir, input_text)

        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()

    user_prompt = render_template(
        user_prompt_template, {"query": query, "content": content}
    )

    if system_prompt is None:
        system_prompt = """
You are an expert of answerting questions based on the content povided by the user.
"""
    response, completion = llm_cli_tool.run_inference_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        need_json=need_json,
        call_target="llm_cli",
        override_model_name=None,
        override_max_token=None,
    )

    return response


@click.command(help="Run LLM prompts from a file.")
@click.option("-q", "--query", "query", required=True, help="the query to run")
@click.option(
    "-i",
    "--input-text",
    "input_text",
    required=False,
    help="the text file to read as the context",
)
@click.option(
    "-p",
    "--user-prompt-file",
    "user_prompt_file",
    required=False,
    default=None,
    help="user prompt template to use, the query and the context will be used as the variables.",
)
@click.option(
    "--system-prompt",
    "system_prompt",
    default=None,
    required=False,
    help="system prompt to use",
)
@click.option(
    "-u",
    "--user",
    "user",
    required=False,
    default=None,
    help="The user to use, default the admin user.",
)
@click.option(
    "-s",
    "--strategy",
    "strategy_name",
    required=False,
    default=None,
    help="The strategy to use.",
)
@common_options
def inference(
    query: str,
    input_text: Optional[str],
    user_prompt_file: Optional[str] = None,
    system_prompt: Optional[str] = None,
    username: Optional[str] = None,
    strategy_name: Optional[str] = None,
    json_output: bool = False,
    indent: int = None,
    **kwargs,
) -> None:
    response = inference_func(
        query=query,
        input_text=input_text,
        user_prompt_file=user_prompt_file,
        system_prompt=system_prompt,
        need_json=json_output,
        username=username,
        strategy_name=strategy_name,
    )
    if json_output:
        result_dict = json.loads(response)
        click.echo(json.dumps(result_dict, indent=indent))
    else:
        click.echo(response)


if __name__ == "__main__":
    inference()
