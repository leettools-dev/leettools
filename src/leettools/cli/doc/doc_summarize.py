from typing import Dict

import click

from leettools.cli.options_common import common_options
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.flow import iterators


@click.command(help="Summarize all documents in the KB that does not have a summary.")
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
    "-f",
    "--force",
    "force",
    is_flag=True,
    default=False,
    help="Force to summarize all documents",
)
@common_options
def summarize_all(
    org_name: str,
    kb_name: str,
    force: bool,
    **kwargs,
) -> None:
    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()  # type: Context
    document_store = context.get_repo_manager().get_document_store()
    docsource_store = context.get_repo_manager().get_docsource_store()
    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()
    display_logger = logger()
    display_logger.set_level("INFO")

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

    from leettools.chat import chat_utils

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query="dummy",
        org_name=org.name,
        kb_name=kb.name,
        username=None,
        strategy_name=None,
        flow_type=None,
        flow_options={},
        display_logger=logger(),
    )

    all_links: Dict[str, int] = {}
    iterators.Summarize.run(
        exec_info=exec_info,
        all_links=all_links,
    )

    for uri in all_links.keys():
        click.echo(f"{uri}: {all_links[uri]}")
