import os
from datetime import datetime
from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.core.consts.docsource_status import DocSourceStatus


@click.command(help="Manually ingest a doc source.")
@click.option(
    "-i",
    "--docsource-uuid",
    "docsource_uuid",
    default=None,
    required=True,
    help="The docsource uuid to ingest.",
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
    help="The knowledgebase to extract.",
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
def ingest(
    docsource_uuid: str,
    kb_name: str,
    org_name: Optional[str] = None,
    username: Optional[str] = None,
    **kwargs,
) -> None:
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = "cli_docsource_ingest"
    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()
    document_store = context.get_repo_manager().get_document_store()
    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()

    if org_name is None:
        org = org_manager.get_default_org()
    else:
        org = org_manager.get_org_by_name(org_name)
        if org is None:
            raise exceptions.ParametersValidationException(
                [f"Organization {org_name} not found"]
            )

    kb = kb_manager.get_kb_by_name(org, kb_name)
    if kb is None:
        raise exceptions.ParametersValidationException(
            [f"Knowledge base {kb_name} not found in Org {org.name}"]
        )

    """
    "123456789012345678901234"
    "66bcf7f2c593676ade4d2a37"
    """
    uid_width = 26

    docsource = docsource_store.get_docsource(org, kb, docsource_uuid)
    if docsource is None:
        raise exceptions.ParametersValidationException(
            [f"Docsource {docsource_uuid} not found in Org {org.name}, KB {kb.name}"]
        )

    if not docsource.is_finished():
        raise exceptions.UnexpectedCaseException(
            f"Docsource {docsource_uuid} is already in {docsource.docsource_status} status."
        )

    docsource.docsource_status = DocSourceStatus.CREATED
    docsource.updated_at = datetime.now()

    update_docsource = docsource_store.update_docsource(org, kb, docsource)
    click.echo("Updated docsource. Waiting for the docsource to be ingested.")

    if docsource_store.wait_for_docsource(org, kb, update_docsource):
        click.echo("Docsource has been ingested.")
    else:
        click.echo("Docsource ingestion failed.")
        click.echo("Please check the docsource status and logs for more information.")
