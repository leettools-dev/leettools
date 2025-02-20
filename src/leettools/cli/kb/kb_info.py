from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.core.schemas.user import User


@click.command(help="Display the metadata for a KB.")
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
    help="The knowledgebase to display.",
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
def info(
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
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_cli_kb_info"

    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()
    user_store = context.get_user_store()

    if username is None:
        user = User.get_admin_user()
    else:
        user = user_store.get_user_by_name(username)
        if user is None:
            raise exceptions.EntityNotFoundException(
                entity_name=username, entity_type="User"
            )

    # we will report error if the org does not exist
    # usually we do not specify the org name
    if org_name is None:
        org = org_manager.get_default_org()
    else:
        org = org_manager.get_org_by_name(org_name)
    if org is None:
        raise exceptions.EntityNotFoundException(
            entity_name=org_name, entity_type="Organization"
        )

    kb = kb_manager.get_kb_by_name(org, kb_name)
    # we will create the kb if it does not exist
    if kb == None:
        click.secho(
            f"Warning: KB {kb_name} does not exist.",
            err=True,
            fg="yellow",
        )
        return

    if json_output:
        click.echo(kb.model_dump_json(indent=indent))
    else:
        click.echo(f"{kb}")
