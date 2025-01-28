from typing import Optional

import click

from leettools.cli.cli_utils import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.common.logging import logger
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.schedule_type import ScheduleType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.schedule_config import ScheduleConfig
from leettools.flow.utils import pipeline_utils


@click.command(help="Add one URL to the kb.")
@click.option(
    "-r",
    "--url",
    "url",
    required=True,
    help="The URL to add to the KB.",
)
@click.option(
    "-g",
    "--org",
    "org_name",
    default=None,
    required=False,
    help="The org to add the documents to.",
)
@click.option(
    "-k",
    "--kb",
    "kb_name",
    default=None,
    required=False,
    help="The knowledgebase to add the documents to.",
)
@click.option(
    "-u",
    "--user",
    "username",
    default=None,
    required=False,
    help="The user to use, default Admin.",
)
@click.option(
    "-c",
    "--chunk_size",
    "chunk_size",
    default=None,
    required=False,
    help="The chunk size for each segment if we have to create a new KB.",
)
@click.option(
    "-s",
    "--scheduler_check",
    "scheduler_check",
    default=True,
    help=(
        "If set to True, start the scheduler or use the system scheduler. If False, "
        "no scheduler check will be performed."
    ),
)
@common_options
def add_url(
    url: str,
    org_name: str,
    kb_name: str,
    username: str,
    chunk_size: str,
    scheduler_check: bool,
    json_output: Optional[bool] = False,
    indent: Optional[int] = 2,
    **kwargs,
) -> None:
    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()  # type: Context
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_add_url_to_kb"
    if scheduler_check == False:
        context.scheduler_is_running = True

    repo_manager = context.get_repo_manager()
    docsource_store = repo_manager.get_docsource_store()
    document_store = repo_manager.get_document_store()

    org, kb, user = setup_org_kb_user(
        context=context,
        org_name=org_name,
        kb_name=kb_name,
        username=username,
        adhoc_kb=True,
    )

    if chunk_size is not None:
        context.settings.DEFAULT_CHUNK_SIZE = int(chunk_size)

    schedule_config: ScheduleConfig = ScheduleConfig(schedule_type=ScheduleType.MANUAL)
    docsource_create = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb.kb_id,
        source_type=DocSourceType.URL,
        display_name=url,
        uri=url,
        schedule_config=schedule_config,
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)

    pipeline_utils.process_docsource_manual(
        org=org,
        kb=kb,
        user=user,
        docsource=docsource,
        context=context,
        display_logger=logger(),
    )

    documents = document_store.get_documents_for_docsource(org, kb, docsource)
    if len(documents) == 0:
        logger().error(f"No documents were found for the URL: {url}")
        return

    if len(documents) > 1:
        logger().error(f"More than one document was found for the URL: {url}")
        return

    document = documents[0]
    if json_output:
        click.echo(document.model_dump_json(indent=indent))
    else:
        click.echo(
            f"org:          \t{org.name}\n"
            f"kb:           \t{kb.name}\n"
            f"docource_id:  \t{docsource.docsource_uuid}\n"
            f"docsink_id:   \t{document.docsink_uuid}\n"
            f"document_uuid:\t{document.document_uuid}\n"
            f"URI:          \t{document.original_uri}"
        )
