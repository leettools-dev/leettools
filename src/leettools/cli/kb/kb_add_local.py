import json
from pathlib import Path

import click

from leettools.cli.cli_utils import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.common.logging import logger
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.schedule_config import ScheduleConfig
from leettools.flow.utils import pipeline_utils


@click.command(help="Add a local dir or file to a kb.")
@click.option(
    "-p",
    "--path",
    "path_str",
    required=True,
    help="The path to add to the repo.",
)
@click.option(
    "-s",
    "--source",
    "doc_source",
    default=None,
    required=False,
    help="The doc source of the documents. If specified, we will use"
    " this string instead of the path string as the doc soure. This way we allow"
    " download and process the files first and add the processed files in batch.",
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
    "--scheduler_check",
    "scheduler_check",
    default=True,
    help=(
        "If set to True, start the scheduler or use the system scheduler. If False, "
        "no scheduler check will be performed."
    ),
)
@common_options
def add_local(
    path_str: str,
    doc_source: str,
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
    path = Path(path_str).absolute()
    if not path.exists():
        logger().error(f"The path {path} does not exist.")
        return
    if doc_source is None:
        doc_source = path.as_uri()

    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()  # type: Context
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_add_local_dir"
    if scheduler_check == False:
        context.scheduler_is_running = True

    repo_manager = context.get_repo_manager()
    docsource_store = repo_manager.get_docsource_store()
    document_store = repo_manager.get_document_store()
    display_logger = logger()

    org, kb, user = setup_org_kb_user(context, org_name, kb_name, username)

    if chunk_size is not None:
        context.settings.DEFAULT_CHUNK_SIZE = int(chunk_size)

    # ingest the docsource
    docsource_create = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb.kb_id,
        source_type=DocSourceType.LOCAL,
        uri=str(path),
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)

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
            user=user,
            docsource=docsource,
            context=context,
            display_logger=display_logger,
        )

    documents = document_store.get_documents_for_docsource(org, kb, docsource)
    if json_output:
        for document in documents:
            click.echo(json.dumps(document, indent=indent))
    else:
        click.echo("org\tkb\tdocsource_id\tdocsink_id\tdocument_uuid\tURI")
        for document in documents:
            click.echo(
                f"{org.name}\t{kb.name}\t{docsource.docsource_uuid}"
                f"\t{document.docsink_uuid}\t{document.document_uuid}"
                f"\t{document.original_uri}"
            )
