from typing import List, Optional, Set

import click

from leettools.cli.cli_utils import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.common.logging import logger
from leettools.core.consts.schedule_type import ScheduleType
from leettools.core.schemas.document import Document
from leettools.flow.utils import pipeline_utils


@click.command(help="Ingest all docsources with a manual schedule in a KB.")
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
    help="The knowledgebase to ingest.",
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
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_cli_kb_ingest"

    docsource_store = context.get_repo_manager().get_docsource_store()
    document_store = context.get_repo_manager().get_document_store()

    display_logger = logger()

    org, kb, user = setup_org_kb_user(context, org_name, kb_name, username)

    uid_width = 35

    if not json_output:
        click.echo(
            f"{'DocSource UUID':<{uid_width}}"
            f"{'DocSink UUID':<{uid_width}}"
            f"{'Document UUID':<{uid_width}}"
            f"Original URI"
        )

    for docsource in docsource_store.get_docsources_for_kb(org, kb):
        if docsource.schedule_config is None:
            continue
        if docsource.schedule_config.schedule_type != ScheduleType.MANUAL:
            continue

        old_documents = document_store.get_documents_for_docsource(org, kb, docsource)
        old_docids: Set[str] = {doc.document_uuid for doc in old_documents}

        updated_docsource = pipeline_utils.process_docsource_manual(
            org=org,
            kb=kb,
            user=user,
            docsource=docsource,
            context=context,
            display_logger=display_logger,
        )

        new_documents = document_store.get_documents_for_docsource(
            org, kb, updated_docsource
        )

        diff_documents: List[Document] = []
        for doc in new_documents:
            if doc.document_uuid not in old_docids:
                diff_documents.append(doc)

        if json_output:
            for doc in diff_documents:
                click.echo(doc.model_dump_json(indent=indent))
        else:
            for doc in diff_documents:
                click.echo(
                    f"{docsource.docsource_uuid:<{uid_width}}"
                    f"{doc.docsink_uuid:<{uid_width}}"
                    f"{doc.document_uuid:<{uid_width}}"
                    f"{doc.original_uri}"
                )
