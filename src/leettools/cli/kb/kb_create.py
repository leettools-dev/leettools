from typing import Optional

import click

from leettools.cli.cli_utils import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.context_manager import ContextManager


@click.command(help="Create a new KB.")
@click.option(
    "--org",
    "org_name",
    default=None,
    required=False,
    help="The org to check.",
)
@click.option(
    "-k",
    "--kb",
    "kb_name",
    required=True,
    help="The knowledgebase name to create.",
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
    "--schedule",
    "schedule",
    is_flag=True,
    help="Add the KB to the scheduler.",
)
@common_options
def create(
    org_name: str,
    kb_name: str,
    username: str,
    schedule: bool,
    json_output: Optional[bool] = False,
    indent: Optional[int] = 2,
    **kwargs,
) -> None:
    """
    Create a new KB.

    If no org_name is specified, we will use the default org.
    If org_name is specified but not found, we will raise an EntityNotFoundException.

    If kb_name already exists, we will show the existing kb info.

    If username is not specified, we will use the default admin user.
    If username is specified but not found, we will raise an EntityNotFoundException.

    If schedule is False, we will create a new adhoc kb. In this case, we will create the
    new kb with the kb_name and set it to auto_schedule=False, which means that the kb
    is excluded from the scheduler. Otherwise the kb will be added to the scheduler.
    """

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_kb_create"

    if schedule:
        adhoc_kb = False
    else:
        adhoc_kb = True

    org, kb, user = setup_org_kb_user(context, org_name, kb_name, username, adhoc_kb)

    if json_output:
        click.echo(kb.model_dump_json(indent=indent))
    else:
        for field in kb.model_fields:
            click.echo(f"{field}: {getattr(kb, field)}")
