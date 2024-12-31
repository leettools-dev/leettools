import click

from leettools.cli.cli_utils import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.flow.metadata.extract_metadata_manager import (
    create_extraction_metadata_manager,
)


@click.command(help="List all the extracted DBs for a KB.")
@click.option(
    "-g",
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
    help="The knowledgebase to check.",
)
@click.option(
    "-u",
    "--user",
    "username",
    default=None,
    required=False,
    help="The user to use.",
)
@common_options
def list_db(
    org_name: str,
    kb_name: str,
    username: str,
    **kwargs,
) -> None:
    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()  # type: Context
    context.is_svc = False
    context.name = "get_db_list"

    org, kb, user = setup_org_kb_user(context, org_name, kb_name, username)

    # TODO: we need a systematic way to record the extracted data
    # collections = kb_manager.get_exracted_collections(kb)
    # filtered_collections = [coll for coll in collections if coll.startswith(prefix)]
    settings = context.settings

    click.echo(f"Name\tType\tItems\tUpdated")
    extract_metadata_manager = create_extraction_metadata_manager(settings)
    for db_name, info_list in extract_metadata_manager.get_extracted_db_info(
        org, kb
    ).items():
        item_count_total = sum([info.item_count for info in info_list])
        last_updated = max([info.created_at for info in info_list])
        info = info_list[0]
        click.echo(f"{db_name}\t{info.db_type}\t{item_count_total}\t{last_updated}")
