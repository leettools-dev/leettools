from typing import Optional

import click

from leettools.chat.history_manager import get_history_manager
from leettools.cli.options_common import common_options
from leettools.core.schemas.chat_query_result import ChatAnswerItemCreate
from leettools.core.schemas.user import User


@click.command(help="Set the content for a section in a query answer.")
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
    "-a",
    "--answer-content-file",
    "answer_content_file",
    required=True,
    help="The file to read the answer content to.",
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
def section_set(
    chat_id: str,
    query_id: str,
    position_in_answer: str,
    answer_content_file: str,
    username: Optional[str] = None,
    **kwargs,
):
    """
    Command line interface to set the content of the specified section.
    """
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    chat_manager = get_history_manager(context)

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

    try:
        with open(answer_content_file, "r", encoding="utf-8") as f:
            answer_content = f.read()
    except Exception as e:
        click.echo(f"Error reading file {answer_content_file}: {e}", err=True)
        return

    found = False
    for answer in chat_query.answers:
        if answer.query_id != query_id:
            continue
        if answer.position_in_answer != position_in_answer:
            continue
        if answer.answer_score < 0:
            continue

        found = True

        caic = ChatAnswerItemCreate(
            chat_id=chat_id,
            query_id=query_id,
            answer_content=answer_content,
            answer_plan=answer.answer_plan,
            position_in_answer=position_in_answer,
            answer_title=answer.answer_title,
            answer_score=1.0,
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
