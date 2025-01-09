from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common.exceptions import (
    EntityNotFoundException,
    ParametersValidationException,
)


@click.command(help="List all segments for a document.")
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
@click.option(
    "-d",
    "--doc",
    "doc_uuid",
    type=str,
    required=True,
    help="The document UUID",
)
@common_options
def list_segments_for_doc(
    org_name: str,
    kb_name: str,
    doc_uuid: str,
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

    doc = document_store.get_document_by_id(org, kb, doc_uuid)
    if doc is None:
        raise EntityNotFoundException(entity_name=doc_uuid, entity_type="Document")

    segment_list = segment_store.get_all_segments_for_document(org, kb, doc_uuid)

    for segment in segment_list:
        if json_output:
            click.echo(segment.model_dump_json(indent=indent))
        else:
            click.echo(segment.model_dump_json(indent=2))
            click.echo("\n")
