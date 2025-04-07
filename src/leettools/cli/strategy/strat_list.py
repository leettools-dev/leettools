from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.core.schemas.user import User


@click.command(help="List all strategies.")
@click.option(
    "-u",
    "--user",
    "username",
    default=None,
    required=False,
    help="The username to list strategies for. If not provided, lists all strategies.",
)
@common_options
def list(
    username: Optional[str],
    active_only: bool = True,
    json_output: bool = False,
    indent: Optional[int] = None,
    **kwargs,
) -> None:
    """
    List strategies in the database.

    Args:
        username: Optional username to filter strategies by user
        active_only: If True, only show active strategies
        json_output: If True, output in JSON format
        indent: Number of spaces for JSON indentation
        **kwargs: Additional keyword arguments from common options
    """
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_strategy_list"

    user_store = context.get_user_store()
    strategy_store = context.get_strategy_store()

    if username is None:
        user = User.get_admin_user()
    else:
        user = user_store.get_user_by_name(username)
        if user is None:
            raise exceptions.EntityNotFoundException(
                entity_name=username, entity_type="User"
            )

    strategies = strategy_store.list_active_strategies_for_user(user)
    for strategy in strategies:
        if json_output:
            click.echo(strategy.model_dump_json(indent=indent))
        else:
            click.echo(
                f"User: {user.username}\tStrategy: {strategy.strategy_name}\t"
                f"ID: {strategy.strategy_id}\tStatus: {strategy.strategy_status}"
            )
