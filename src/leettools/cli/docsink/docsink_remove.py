from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions


@click.command(help="Remove a DocSink in a KB.")
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
    help="The knowledgebase to list.",
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
    "-i",
    "--docsink-uuid",
    "docsink_uuid",
    default=None,
    required=True,
    help="The DocSink UUID",
)
@common_options
def remove(
    kb_name: str,
    docsink_uuid: str,
    org_name: Optional[str] = None,
    username: Optional[str] = None,
    **kwargs,
) -> None:
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_docsrc_list"
    docsink_store = context.get_repo_manager().get_docsink_store()
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

    docsink = docsink_store.get_docsink_by_id(org, kb, docsink_uuid)
    if docsink is None:
        raise exceptions.EntityNotFoundException(
            entity_name=docsink_uuid, entity_type="DocSink"
        )

    if docsink.is_deleted:
        click.echo(f"DocSink {docsink_uuid} has been marked as deleted.")
        return

    uri = docsink.original_doc_uri
    if uri is None or uri == "":
        uri = docsink.raw_doc_uri
    click.echo(f"DocSink {uri} removed from KB {kb.name} in Org {org.name}")
