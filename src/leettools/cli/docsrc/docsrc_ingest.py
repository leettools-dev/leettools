import os
from datetime import datetime
from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.eds.scheduler.scheduler_manager import run_scheduler


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
@click.option(
    "-j",
    "--json",
    "json_output",
    is_flag=True,
    required=False,
    help="Output the full record results in JSON format.",
)
@click.option(
    "--indent",
    "indent",
    default=None,
    type=int,
    required=False,
    help="The number of spaces to indent the JSON output.",
)
@common_options
def ingest(
    docsource_uuid: str,
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
    context.name = "cli_docsource_ingest"
    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()
    document_store = context.get_repo_manager().get_document_store()
    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()
    display_logger = logger()

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

    docsource.docsource_status = DocSourceStatus.CREATED
    docsource.updated_at = datetime.now()
    docsource_store.update_docsource(org, kb, docsource)

    display_logger.info("Updated docsource. Waiting for the docsource to be ingested.")

    if context.scheduler_is_running:
        display_logger.info("Scheduled the new DocSource to be processed ...")
        started = False
    else:
        display_logger.info("Start the scheduler to process the new DocSource ...")
        started = run_scheduler(context=context)

    if started == False:
        # another process is running the scheduler
        finished = docsource_store.wait_for_docsource(
            org, kb, docsource, timeout_in_secs=300
        )
        if finished == False:
            display_logger.warning(
                "The document source has not finished processing yet."
            )
        else:
            display_logger.info("The document source has finished processing.")
            docsource.docsource_status = DocSourceStatus.COMPLETED
            docsource_store.update_docsource(org, kb, docsource)
    else:
        # the scheduler has been started and finished processing
        display_logger.info("Docsource has been ingested.")

    docsource = docsource_store.get_docsource(org, kb, docsource_uuid)
    if json_output:
        click.echo(docsource.model_dump_json(indent=indent))
    else:
        click.echo(
            f"{docsource.docsource_uuid:<{uid_width}}"
            f"{docsource.docsource_status:<15}"
            f"{docsource.display_name:<40}"
            f"{docsource.uri}"
        )
