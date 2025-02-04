from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions


@click.command(help="List all DocSource in a KB.")
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
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_docsrc_list"
    docsource_store = context.get_repo_manager().get_docsource_store()
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

    uid_width = 36

    docsources = docsource_store.get_docsources_for_kb(org, kb)
    if not json_output:
        click.echo(
            f"{'DocSource UUID':<{uid_width}} {'Created at':<19} {'Status':<15} {'Display Name':<40} URI"
        )

    for docsource in docsources:
        if json_output:
            click.echo(docsource.model_dump_json(indent=indent))
        else:
            display_name = docsource.display_name
            if display_name is None:
                display_name = "None"
            created_at = docsource.created_at.strftime("%Y-%m-%d %H:%M:%S")
            click.echo(
                f"{docsource.docsource_uuid:<{uid_width}} "
                f"{created_at:<19} "
                f"{docsource.docsource_status.value:<15} "
                f"{display_name:<40} "
                f"{docsource.uri}"
            )
