from typing import Optional

import click

from leettools.cli.cli_utils import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.utils import time_utils
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
@click.option(
    "--use-scheduler",
    "use_scheduler",
    is_flag=True,
    help="If the KB is set to auto_schedule, force to use the scheduler. No effect if the KB is not set to auto_schedule.",
)
@common_options
def ingest(
    docsource_uuid: str,
    kb_name: str,
    org_name: Optional[str] = None,
    username: Optional[str] = None,
    use_scheduler: bool = False,
    json_output: bool = False,
    indent: int = None,
    **kwargs,
) -> None:
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_docsource_ingest"
    docsource_store = context.get_repo_manager().get_docsource_store()

    display_logger = logger()

    org, kb, user = setup_org_kb_user(context, org_name, kb_name, username)

    uid_width = 35

    docsource = docsource_store.get_docsource(org, kb, docsource_uuid)
    if docsource is None:
        raise exceptions.ParametersValidationException(
            [f"Docsource {docsource_uuid} not found in Org {org.name}, KB {kb.name}"]
        )

    docsource.docsource_status = DocSourceStatus.CREATED
    docsource.updated_at = time_utils.current_datetime()
    docsource_store.update_docsource(org, kb, docsource)

    if use_scheduler and kb.auto_schedule:
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
            user=user,
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
