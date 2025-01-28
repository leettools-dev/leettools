import click

from leettools.chat.history_manager import get_history_manager
from leettools.cli.options_common import common_options


@click.command(help="Run query.")
@click.option(
    "-q",
    "--query",
    "query",
    required=True,
    help="the question to ask",
)
@click.option(
    "-g",
    "--org",
    "org_name",
    default=None,
    required=False,
    help="The org to add the documents to.",
)
@click.option(
    "-s",
    "--strategy",
    "strategy_name",
    default=None,
    required=False,
    help="The strategy to use.",
)
@click.option(
    "-k",
    "--kb",
    "kb_name",
    default=None,
    required=False,
    help="The knowledgebase to add the documents to.",
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
def run(
    query: str,
    org_name: str,
    kb_name: str,
    username: str,
    strategy_name: str,
    **kwargs,
):
    """
    Command line interface to use the local repo to answer the input query.
    """

    from leettools.context_manager import Context, ContextManager

    context = ContextManager().get_context()  # type: Context
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_query"
    chat_manager = get_history_manager(context)

    from leettools.chat import chat_utils

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org_name,
        kb_name=kb_name,
        username=username,
        strategy_name=strategy_name,
        flow_options={},
        display_logger=None,
    )

    chat_query_result = chat_manager.run_query_with_strategy(
        org=exec_info.org,
        kb=exec_info.kb,
        user=exec_info.user,
        chat_query_item_create=exec_info.target_chat_query_item,
        chat_query_options=exec_info.chat_query_options,
        strategy=exec_info.strategy,
    )
    for chat_answer_item_create in chat_query_result.chat_answer_item_list:
        print(chat_answer_item_create.answer_content)
