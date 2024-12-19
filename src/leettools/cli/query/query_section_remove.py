from typing import Optional

import click

from leettools.chat.history_manager import get_history_manager
from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.core.schemas.chat_query_result import ChatAnswerItemCreate
from leettools.core.schemas.user import User


@click.command(help="Remove a section at the specified position.")
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
    help=(
        "The position in the answer to add the section to, the sections after it will "
        "be moved down."
    ),
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
def section_remove(
    chat_id: str,
    query_id: str,
    position_in_answer: str,
    org_name: Optional[str] = None,
    username: Optional[str] = None,
    **kwargs,
):
    """
    Command line interface to remove a section from the answer.
    """
    from leettools.context_manager import ContextManager

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

    kb_id = chat_query.kb_id
    kb = kb_manager.get_kb_by_id(org, kb_id)
    if kb is None:
        raise exceptions.EntityNotFoundException(
            entity_name=kb_id, entity_type="KnowledgeBase"
        )

    updated_chat_query = chat_manager.remove_answer_item_from_chat(
        username=username,
        chat_id=chat_id,
        query_id=query_id,
        position_in_answer=position_in_answer,
    )

    if updated_chat_query is None:
        click.echo(f"Answer for chat {chat_id} query {query_id} is not updated.")
    else:
        click.echo(
            f"Removed section for chat {chat_id} query {query_id} pos {position_in_answer}"
        )
