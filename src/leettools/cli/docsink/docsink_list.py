from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions


@click.command(help="List all DocSink in a KB.")
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
@common_options
def list(
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
    context.name = "cli_docsrc_list"
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

    uid_width = 35

    docsinks = docsink_store.get_docsinks_for_kb(org, kb)
    for docsink in docsinks:
        if json_output:
            click.echo(docsink.model_dump_json(indent=indent))
        else:
            click.echo(
                f"{docsink.docsink_uuid:<{uid_width}} "
                f"{docsink.docsink_status:<15} "
                f"{docsink.original_doc_uri} "
                f"{docsink.raw_doc_uri} "
                f"{docsink.expired_at} "
            )
