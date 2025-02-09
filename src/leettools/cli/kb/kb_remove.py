import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.context_manager import ContextManager
from leettools.core.schemas.user import User


@click.command(help="Remove an existing KB.")
@click.option(
    "--org",
    "org_name",
    default=None,
    required=False,
    help="The org to check.",
)
@click.option(
    "-k",
    "--kb",
    "kb_name",
    required=True,
    help="The knowledgebase name to remove.",
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
def remove(
    org_name: str,
    kb_name: str,
    username: str,
    **kwargs,
) -> None:
    """
    Remove an existing KB.

    If no org_name is specified, we will use the default org.
    If org_name is specified but not found, we will raise an EntityNotFoundException.

    If kb_name does not exist, we will print a warning message and return.

    If username is not specified, we will use the default admin user.
    If username is specified but not found, we will raise an EntityNotFoundException.
    """

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_kb_create"

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

    # We do not check the permission for CLI applications
    if kb_manager.delete_kb_by_name(org, kb_name):
        click.secho(f"KB {kb_name} has been successfully removed.", fg="green")
    else:
        # this should not happen
        click.secho(f"Failed to remove KB {kb_name}.", fg="red")
