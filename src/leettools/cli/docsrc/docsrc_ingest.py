from datetime import datetime
from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.flow.utils import pipeline_utils


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
    json_output: bool = False,
    indent: int = None,
    **kwargs,
) -> None:
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = "cli_docsource_ingest"
    docsource_store = context.get_repo_manager().get_docsource_store()
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

    if kb.auto_schedule:
        pipeline_utils.process_docsources_auto(
            org=org,
            kb=kb,
            docsources=[docsource],
            context=context,
            display_logger=display_logger,
        )
    else:
        pipeline_utils.process_docsource_manual(
            org=org,
            kb=kb,
            docsource=docsource,
            context=context,
            display_logger=display_logger,
        )

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
