from typing import List, Optional, Set

import click

from leettools.cli.cli_utils import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.common.logging import logger
from leettools.core.consts.schedule_type import ScheduleType
from leettools.core.schemas.document import Document
from leettools.flow.utils import pipeline_utils


@click.command(help="Display the metadata for a KB.")
@click.option(
    "-g",
    "--org",
    "org_name",
    default=None,
    required=False,
    help="The target org, org-default is not specified.",
)
@click.option(
    "-k",
    "--kb",
    "kb_name",
    default=None,
    required=True,
    help="The knowledgebase to display.",
)
@click.option(
    "-u",
    "--user",
    "username",
    default=None,
    required=False,
    help="The user to use, default the admin user.",
)
@common_options
def info(
    kb_name: str,
    org_name: Optional[str] = None,
    username: Optional[str] = None,
    json_output: bool = False,
    indent: int = None,
    **kwargs,
) -> None:
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_cli_kb_info"

    display_logger = logger()

    org, kb, user = setup_org_kb_user(context, org_name, kb_name, username)

    if json_output:
        click.echo(kb.model_dump_json(indent=indent))
    else:
        click.echo(f"{kb}")
