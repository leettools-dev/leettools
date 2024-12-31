import click

from leettools.cli.options_common import common_options


@click.command(help="List all knowledgebases.")
@click.option(
    "-o",
    "--org",
    "org_name",
    default=None,
    required=False,
    help="The org to list the knowledgebases for.",
)
@click.option(
    "-j",
    "--json",
    "json_output",
    is_flag=True,
    required=False,
    help="Output the full record results in JSON format.",
)
@click.option(
    "--indent",
    "indent",
    default=None,
    type=int,
    required=False,
    help="The number of spaces to indent the JSON output.",
)
@common_options
def list(
    org_name: str, json_output: bool = False, indent: int = None, **kwargs
) -> None:

    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()
    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()
    if org_name is None:
        for org in org_manager.list_orgs():
            for kb in kb_manager.get_all_kbs_for_org(org):
                if json_output:
                    click.echo(kb.model_dump_json(indent=indent))
                else:
                    click.echo(f"Org: {org.name}\tKB: {kb.name}\tID: {kb.kb_id}")
    else:
        org = org_manager.get_org_by_name(org_name)
        if org is None:
            click.echo(f"Org {org_name} does not exist.", err=True)
            return
        for kb in kb_manager.get_all_kbs_for_org(org):
            if json_output:
                click.echo(kb.model_dump_json(indent=indent))
            else:
                click.echo(f"Org: {org.name}\tKB: {kb.name}\tID: {kb.kb_id}")
