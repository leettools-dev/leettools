import json
from typing import Dict, Optional

import click

from leettools.chat import chat_utils
from leettools.chat.history_manager import get_history_manager
from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.core.schemas.chat_query_result import ChatAnswerItemCreate
from leettools.core.schemas.user import User
from leettools.flow.exec_info import ExecInfo
from leettools.flow.schemas.article import ArticleSection, ArticleSectionPlan
from leettools.flow.utils import flow_utils


@click.command(help="Generate the section again with new prompts/title.")
@click.option(
    "-c",
    "--chat_id",
    "chat_id",
    required=True,
    help="The chat id to get the answers for.",
)
@click.option(
    "-q",
    "--query_id",
    "query_id",
    required=True,
    help="The query id to get the answers for.",
)
@click.option(
    "-p",
    "--position-in-answer",
    "position_in_answer",
    required=True,
    help="The position in the answer to get the content for.",
)
@click.option(
    "-t",
    "--prompt-file",
    "prompt_file",
    required=True,
    help="The file to read the prompts and titles",
)
@click.option(
    "-o",
    "--org",
    "org_name",
    default=None,
    required=False,
    help="The org to add the documents to.",
)
@click.option(
    "-u",
    "--user",
    "username",
    required=False,
    default=None,
    help="The user to use, default the admin user.",
)
@common_options
def section_regen(
    chat_id: str,
    query_id: str,
    position_in_answer: str,
    prompt_file: str,
    org_name: Optional[str] = None,
    username: Optional[str] = None,
    **kwargs,
):
    """
    Command line interface to regenerate the specified section using a promt file.
    """
    from leettools.context_manager import ContextManager
    from leettools.flow import subflows

    context = ContextManager().get_context()
    chat_manager = get_history_manager(context)
    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()

    if org_name is None:
        org = org_manager.get_default_org()
    else:
        org = org_manager.get_org_by_name(org_name)
        if org is None:
            raise exceptions.EntityNotFoundException(
                entity_name=org_name, entity_type="Organization"
            )
    userstore = context.get_user_store()
    if username is None:
        user = User.get_admin_user()
        username = user.username
    else:
        user = userstore.get_user_by_name(username)
        if user is None:
            click.echo(f"User {username} does not exist.", err=True)
            return

    chat_manager = get_history_manager(context)

    chat_query = chat_manager.get_ch_entry(username=user.username, chat_id=chat_id)
    if chat_query is None:
        click.echo(f"Chat id {chat_id} does not exist.", err=True)
        return

    prompt_dict: Dict[str, str] = {}
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_dict = json.loads(f.read())
    except Exception as e:
        click.echo(f"Error reading file {prompt_file}: {e}", err=True)
        return
    click.echo(f"Prompt dict: {prompt_dict}")

    found = False

    flow_options = {}

    global_answer_source_itemss = chat_query.answers[0].answer_source_items

    for query in chat_query.queries:
        if query.query_id != query_id:
            continue
        if query.chat_query_options is not None:
            flow_options = query.chat_query_options.flow_options
            break

    sections = []
    for answer in chat_query.answers:
        if answer.answer_score < 0:
            continue

        if answer.query_id != query_id:
            continue

        if answer.position_in_answer != position_in_answer:
            sections.append(
                ArticleSection(
                    title=answer.answer_title,
                    content=answer.answer_content,
                    plan=answer.answer_plan,
                )
            )
            continue

        found = True

        section_plan = answer.answer_plan

        if section_plan is None:
            section_plan = ArticleSectionPlan(
                title=prompt_dict.get("title", ""),
                user_prompt_template=prompt_dict.get("user_prompt_template", ""),
                system_prompt_template=prompt_dict.get("system_prompt_template", ""),
                search_query=prompt_dict.get("search_query", ""),
            )
            # TODO: check if the empty plan would work.
        else:
            if "title" in prompt_dict:
                section_plan.title = prompt_dict["title"]
            if "user_prompt_template" in prompt_dict:
                section_plan.user_prompt_template = prompt_dict["user_prompt_template"]
            if "system_prompt_template" in prompt_dict:
                section_plan.system_prompt_template = prompt_dict[
                    "system_prompt_template"
                ]
            if "search_query" in prompt_dict:
                section_plan.search_query = prompt_dict["search_query"]

        kb_id = chat_query.kb_id
        kb = kb_manager.get_kb_by_id(org, kb_id)
        if kb is None:
            raise exceptions.EntityNotFoundException(
                entity_name=kb_id, entity_type="KnowledgeBase"
            )

        exec_info = chat_utils.setup_exec_info(
            context=context,
            query=section_plan.search_query,
            org_name=org.name,
            kb_name=kb.name,
            username=username,
            strategy_name=None,
            flow_options=flow_options,
            display_logger=None,
        )

        new_section = subflows.SubflowGenSection.run_subflow(
            exec_info=exec_info,
            section_plan=section_plan,
            accumulated_source_items=global_answer_source_itemss,
            previous_sections=sections,
        )

        caic = ChatAnswerItemCreate(
            chat_id=chat_id,
            query_id=query_id,
            answer_content=new_section.content,
            answer_plan=new_section.plan,
            position_in_answer=position_in_answer,
            answer_title=new_section.title,
            answer_score=1.0,
            answer_source_items=global_answer_source_itemss,
        )

        updated_chat_query = chat_manager.update_ch_entry_answer(
            username=username,
            chat_id=chat_id,
            query_id=query_id,
            position_in_answer=position_in_answer,
            new_answer=caic,
        )

        if updated_chat_query is None:
            click.echo(
                f"Answer for chat {chat_id} query {query_id} pos {position_in_answer} is not updated."
            )
        else:
            click.echo(
                f"Updated answer for chat {chat_id} query {query_id} pos {position_in_answer}"
            )
        break

    if not found:
        click.echo(
            f"Answer for chat {chat_id} query {query_id} pos {position_in_answer} is not found."
        )
