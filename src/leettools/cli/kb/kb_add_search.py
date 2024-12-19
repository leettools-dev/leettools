import click

from leettools.cli.cli_util import setup_org_kb_user
from leettools.cli.options_common import common_options
from leettools.core.consts import flow_option
from leettools.core.consts.retriever_type import RetrieverType
from leettools.flow.exec_info import ExecInfo


@click.command(help="Add a web search result docsource to the kb.")
@click.option("-q", "--query", "query", required=True, help="The search query")
@click.option(
    "-r",
    "--retriever",
    "retriever",
    required=False,
    type=click.Choice([r for r in RetrieverType]),
    default=RetrieverType.GOOGLE,
    help="The search engine to use, the default is google",
)
@click.option(
    "-m",
    "--max-results",
    "max_results",
    required=False,
    default=10,
    help="The maximum number of results to return",
)
@click.option(
    "-d",
    "--days-limit",
    "days_limit",
    required=False,
    default=7,
    help="The number of days to limit the search results",
)
@click.option(
    "-o",
    "--org-name",
    "org_name",
    required=False,
    default=None,
    help="The name of the organization to store the search results in",
)
@click.option(
    "-k",
    "--kb-name",
    "kb_name",
    required=False,
    default=None,
    help="The name of the knowledgebase to store the search results in.",
)
@click.option(
    "-u",
    "--user-name",
    "username",
    required=False,
    default=None,
    help="The name of the user to store the search results in, default Admin",
)
@click.option(
    "-c",
    "--chunk_size",
    "chunk_size",
    default=None,
    required=False,
    help="The chunk size for each segment if we have to create a new KB.",
)
@click.option(
    "-s",
    "--scheduler_check",
    "scheduler_check",
    default=True,
    help=(
        "If set to True, start the scheduler or use the system scheduler. If False, "
        "no scheduler check will be performed."
    ),
)
@common_options
def add_search(
    query: str,
    retriever: RetrieverType,
    max_results: int,
    days_limit: int,
    org_name: str,
    kb_name: str,
    username: str,
    chunk_size: str,
    scheduler_check: bool,
    **kwargs,
) -> None:
    from leettools.context_manager import ContextManager
    from leettools.flow import steps
    from leettools.web.web_searcher import WebSearcher

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = "add_search_to_kb"
    if scheduler_check == False:
        context.scheduler_is_running = True

    repo_manager = context.get_repo_manager()
    docsource_store = repo_manager.get_docsource_store()
    document_store = repo_manager.get_document_store()

    org, kb, user = setup_org_kb_user(context, org_name, kb_name, username)

    if chunk_size is not None:
        context.settings.DEFAULT_CHUNK_SIZE = int(chunk_size)

    output_language = "en"
    search_language = "en"

    from leettools.chat import chat_utils

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org_name,
        kb_name=kb_name,
        username=username,
        strategy_name=None,
        flow_options={
            flow_option.FLOW_OPTION_RETRIEVER_TYPE: retriever,
            flow_option.FLOW_OPTION_DAYS_LIMIT: days_limit,
            flow_option.FLOW_OPTION_SEARCH_MAX_RESULTS: max_results,
            flow_option.FLOW_OPTION_OUTPUT_LANGUAGE: output_language,
            flow_option.FLOW_OPTION_SEARCH_LANGUAGE: search_language,
            flow_option.FLOW_OPTION_SUMMARIZING_MODEL: "gpt-4o-mini",
            flow_option.FLOW_OPTION_WRITING_MODEL: "gpt-4o-mini",
        },
        display_logger=None,
    )

    web_searcher = WebSearcher(context)
    docsource = steps.step_search_to_docsource(
        exec_info=exec_info,
        query=query,
        web_searcher=web_searcher,
    )

    documents = document_store.get_documents_for_docsource(org, kb, docsource)
    click.echo("org\tkb\tdocsource_id\tdocsink_id\tdocument_uuid\tURI")
    for document in documents:
        click.echo(
            f"{org.name}\t{kb.name}\t{document.docsource_uuid}"
            f"\t{document.docsink_uuid}\t{document.document_uuid}"
            f"\t{document.original_uri}"
        )


if __name__ == "__main__":
    add_search()
