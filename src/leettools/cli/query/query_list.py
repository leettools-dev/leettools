from typing import Optional

import click

from leettools.chat.history_manager import get_history_manager
from leettools.cli.options_common import common_options
from leettools.core.schemas.user import User


@click.command(help="List all queries for a user.")
@click.option(
    "-u",
    "--user",
    "username",
    required=False,
    default=None,
    help="The user to use, default the admin user.",
)
@common_options
def list(
    username: Optional[str] = None,
    **kwargs,
):
    """
    Command line interface to list all queries for a KB and user.
    """

    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()
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
    chat_query_list = chat_manager.get_ch_entries_by_username(username=username)

    for ch in chat_query_list:
        queries = ch.queries
        for query in queries:
            click.echo(
                f"ChatId: {query.chat_id}\ttype:{ch.article_type}\tQueryId: {query.query_id}\tQuery: {query.query_content}\n"
            )
