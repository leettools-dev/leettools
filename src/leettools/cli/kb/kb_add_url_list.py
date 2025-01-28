from pathlib import Path
from typing import List

import click

from leettools.cli.cli_utils import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.common.logging import logger
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.schedule_type import ScheduleType
from leettools.core.schemas.docsource import DocSource, DocSourceCreate
from leettools.core.schemas.schedule_config import ScheduleConfig
from leettools.flow.utils import pipeline_utils


@click.command(help="Add a list of URLs to the kb.")
@click.option(
    "-f",
    "--file",
    "filename",
    required=True,
    help="The filename that contains the list of URLs.",
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
    help="The user to use.",
)
@click.option(
    "-c",
    "--chunk_size",
    "chunk_size",
    default=None,
    required=False,
    help="The chunk size for each segment.",
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
def add_url_list(
    filename: str,
    org_name: str,
    kb_name: str,
    username: str,
    chunk_size: str,
    scheduler_check: bool,
    json_output: bool,
    indent: int,
    **kwargs,
) -> None:
    """Add a local directory to repository."""
    file_path = Path(filename).absolute()
    if not file_path.exists():
        logger().error(f"The filename path {file_path} does not exist.")
        return

    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()  # type: Context
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_add_local_file_url_list"
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

    docsources: List[DocSource] = []
    schedule_config: ScheduleConfig = ScheduleConfig(schedule_type=ScheduleType.MANUAL)
    # read the file_path line by line and create
    for line in file_path.open():
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        docsource_create = DocSourceCreate(
            org_id=org.org_id,
            kb_id=kb.kb_id,
            source_type=DocSourceType.URL,
            display_name=line,
            uri=line,
            schedule_config=schedule_config,
        )
        docsource = docsource_store.create_docsource(org, kb, docsource_create)
        docsources.append(docsource)

    for docsource in docsources:
        pipeline_utils.process_docsource_manual(
            org=org,
            kb=kb,
            user=user,
            docsource=docsource,
            context=context,
            display_logger=logger(),
        )

    if not json_output:
        click.echo("org\tkb\tdocsource_id\tdocsink_id\tdocument_uuid\tURI")
    for docsource in docsources:
        documents = document_store.get_documents_for_docsource(org, kb, docsource)
        if documents:
            if json_output:
                for document in documents:
                    click.echo(document.model_dump_json(indent=indent))
            else:
                for document in documents:
                    click.echo(
                        f"{org.name}\t{kb.name}\t{docsource.docsource_uuid}\t"
                        f"{document.docsink_uuid}\t{document.document_uuid}\t"
                        f"{document.original_uri}"
                    )
