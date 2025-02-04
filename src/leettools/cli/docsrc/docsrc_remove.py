from datetime import datetime
from typing import Optional

import click

from leettools.cli.cli_utils import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.flow.utils import pipeline_utils


@click.command(help="Remove a DocSource and its documents.")
@click.option(
    "-i",
    "--docsource-uuid",
    "docsource_uuid",
    default=None,
    required=True,
    help="The docsource uuid to remove.",
)
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
    help="The target knowledgebase.",
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
def remove(
    docsource_uuid: str,
    kb_name: str,
    org_name: Optional[str] = None,
    username: Optional[str] = None,
    **kwargs,
) -> None:
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_docsource_ingest"
    docsource_store = context.get_repo_manager().get_docsource_store()

    display_logger = logger()

    org, kb, user = setup_org_kb_user(context, org_name, kb_name, username)

    docsource = docsource_store.get_docsource(org, kb, docsource_uuid)
    if docsource is None:
        raise exceptions.ParametersValidationException(
            [f"Docsource {docsource_uuid} not found in Org {org.name}, KB {kb.name}"]
        )

    if docsource.is_deleted:
        click.echo(f"Docsource {docsource_uuid} has already been marked deleted.")
        return

    docsource_store.delete_docsource(org, kb, docsource)
    uri = docsource.uri
    click.echo(f"Docsource {uri} removed from KB {kb.name} in Org {org.name}")
