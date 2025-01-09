from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common.exceptions import ParametersValidationException


@click.command(help="List all segments for all documents in a KB.")
@click.option(
    "-o",
    "--org",
    "org_name",
    type=str,
    required=False,
    default=None,
    help="The organization name",
)
@click.option(
    "-k",
    "--kb",
    "kb_name",
    type=str,
    required=True,
    help="The knowledge base name",
)
@common_options
def list_all_segements(
    org_name: str,
    kb_name: str,
    json_output: Optional[bool] = False,
    indent: Optional[int] = None,
    **kwargs,
) -> None:

    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()  # type: Context
    segment_store = context.get_repo_manager().get_segment_store()
    document_store = context.get_repo_manager().get_document_store()
    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()

    if org_name is None:
        org = org_manager.get_default_org()
    else:
        org = org_manager.get_org_by_name(org_name)
        if org is None:
            raise ParametersValidationException([f"Organization {org_name} not found"])

    kb = kb_manager.get_kb_by_name(org, kb_name)
    if kb is None:
        raise ParametersValidationException(
            [f"Knowledge base {kb_name} not found in Org {org.name}"]
        )

    documents = document_store.get_documents_for_kb(org, kb)
    for doc in documents:
        if json_output:
            segment_list = segment_store.get_all_segments_for_document(
                org, kb, doc.document_uuid
            )
            for segment in segment_list:
                click.echo(segment.model_dump_json(indent=indent))
        else:
            click.echo(f"Document: {doc.document_uuid}\t{doc.doc_uri}\n")
            segment_list = segment_store.get_all_segments_for_document(
                org, kb, doc.document_uuid
            )
            for segment in segment_list:
                click.echo(segment.model_dump_json(indent=2))
                click.echo("\n")
