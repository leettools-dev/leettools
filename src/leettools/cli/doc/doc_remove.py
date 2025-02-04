import click

from leettools.cli.options_common import common_options
from leettools.common.exceptions import (
    EntityNotFoundException,
    ParametersValidationException,
)


@click.command(help="Remove a document.")
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
    "-i",
    "--doc-uuid",
    "doc_uuid",
    type=str,
    required=True,
    help="The document UUID",
)
@common_options
def remove(
    org_name: str,
    kb_name: str,
    doc_uuid: str,
    **kwargs,
) -> None:
    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()  # type: Context
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

    document_store.delete_document(org, kb, doc)
    uri = doc.original_uri
    if uri is None or uri == "":
        uri = doc.doc_uri
    click.echo(f"Document {uri} removed from KB {kb.name} in Org {org.name}")
