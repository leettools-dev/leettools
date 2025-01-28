from typing import Optional

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.context_manager import Context
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
    default=None,
    required=False,
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
    org_name: Optional[str] = None,
    kb_name: Optional[str] = None,
    username: Optional[str] = None,
    json_output: Optional[bool] = False,
    indent: Optional[int] = 2,
    **kwargs,
) -> None:
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()  # type: Context
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_get_db_list"

    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()

    if org_name is None:
        org = org_manager.get_default_org()
    else:
        org = org_manager.get_org_by_name(org_name)
    if org is None:
        raise exceptions.EntityNotFoundException(
            entity_name=org_name, entity_type="Organization"
        )

    def _show_db_list_for_kb():
        settings = context.settings
        extract_metadata_manager = create_extraction_metadata_manager(settings)
        for db_name, info_list in extract_metadata_manager.get_extracted_db_info(
            org, kb
        ).items():
            if json_output:
                for info in info_list:
                    click.echo(info.model_dump_json(indent=indent))
            else:
                item_count_total = sum([info.item_count for info in info_list])
                last_updated = max([info.created_at for info in info_list])
                info = info_list[0]
                click.echo(
                    f"{kb.name}\t{db_name}\t{info.db_type}\t{item_count_total}\t{last_updated}"
                )

    if not json_output:
        click.echo(f"KnowledgeBase\tExtractDBName\tType\tItems\tUpdated")

    if kb_name is None:
        for kb in kb_manager.get_all_kbs_for_org(org):
            _show_db_list_for_kb()
    else:
        kb = kb_manager.get_kb_by_name(org, kb_name)
        if kb is None:
            raise exceptions.EntityNotFoundException(
                entity_name=kb_name, entity_type="KnowledgeBase"
            )
        _show_db_list_for_kb()
