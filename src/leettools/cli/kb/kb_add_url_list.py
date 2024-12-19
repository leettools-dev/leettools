from pathlib import Path

import click

from leettools.cli.cli_util import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.common.exceptions import UnexpectedOperationFailureException
from leettools.common.logging import logger
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.eds.scheduler.scheduler_manager import run_scheduler


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
    context.name = "add_local_file_url_list"
    if scheduler_check == False:
        context.scheduler_is_running = True

    repo_manager = context.get_repo_manager()
    docsource_store = repo_manager.get_docsource_store()
    document_store = repo_manager.get_document_store()

    org, kb, user = setup_org_kb_user(context, org_name, kb_name, username)

    if chunk_size is not None:
        context.settings.DEFAULT_CHUNK_SIZE = int(chunk_size)

    # read the file_path line by line and create
    for line in file_path.open():
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        docsource_create = DocSourceCreate(
            kb_id=kb.kb_id,
            source_type=DocSourceType.URL,
            display_name=line,
            uri=line,
        )
        docsource = docsource_store.create_docsource(org, kb, docsource_create)

    # start the scheduler
    if context.scheduler_is_running:
        started = False
    else:
        # start the scheduler, if started is false, we are using the system scheduler
        # so that we have to wait for the docsource to finish.
        started = run_scheduler(context)

    if started == False:
        finished = docsource_store.wait_for_docsource(
            org, kb, docsource, timeout_in_secs=None
        )
        if finished == False:
            raise UnexpectedOperationFailureException(
                "The doc source has not been finished."
            )

    documents = document_store.get_documents_for_docsource(org, kb, docsource)
    click.echo("org\tkb\tdocsource_id\tdocsink_id\tdocument_uuid\tURI")
    for document in documents:
        click.echo(
            f"{org.name}\t{kb.name}\t{docsource.docsource_uuid}"
            f"\t{document.docsink_uuid}\t{document.document_uuid}"
            f"\t{document.original_uri}"
        )
