from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions


@click.command(help="List all documents in a KB or a docsource.")
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
@click.option(
    "--docsource-id",
    "docsource_uuid",
    default=None,
    required=False,
    help="The docsource to extract. If not specified, the KB will be extracted.",
)
@common_options
def list(
    kb_name: str,
    org_name: Optional[str] = None,
    username: Optional[str] = None,
    docsource_uuid: Optional[str] = None,
    **kwargs,
) -> None:
    from leettools.context_manager import ContextManager
    from leettools.flow.flows.extractor.flow_extractor import FlowExtractor

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = FlowExtractor.FLOW_TYPE
    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()
    document_store = context.get_repo_manager().get_document_store()
    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()

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

    def traverse_docsource():
        docsinks = docsink_store.get_docsinks_for_docsource(org, kb, docsource)

        for docsink in docsinks:
            documents = document_store.get_documents_for_docsink(org, kb, docsink)
            if len(documents) == 0:
                continue

            # the list should only have one document unless we support
            # multiple versions of the same document in the future
            document = documents[0]

            doc_original_uri = document.original_uri
            if doc_original_uri is None:
                doc_original_uri = document.doc_uri

            click.echo(
                f"{document.docsink_uuid:<{uid_width}}"
                f"{document.document_uuid:<{uid_width}}"
                f"{doc_original_uri}"
            )

    click.echo(
        f"{'DocSource UUID':<{uid_width}}"
        f"{'Document UUID':<{uid_width}}"
        f"Original URI"
    )
    if docsource_uuid is not None:
        docsource = docsource_store.get_docsource(org, kb, docsource_uuid)
        traverse_docsource()
    else:
        docsources = docsource_store.get_docsources_for_kb(org, kb)
        for docsource in docsources:
            traverse_docsource()
