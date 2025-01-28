import traceback
from typing import Any, Dict

import click

from leettools.chat import chat_utils
from leettools.chat.history_manager import get_history_manager
from leettools.cli import cli_utils
from leettools.cli.cli_utils import DELIM_LINE, load_params_from_file, parse_name_value
from leettools.cli.options_common import common_options
from leettools.common.logging import logger
from leettools.context_manager import ContextManager
from leettools.core.knowledgebase.kb_manager import get_kb_name_from_query
from leettools.flow.flow_manager import FlowManager
from leettools.flow.flow_type import FlowType
from leettools.flow.utils import flow_utils


def _run_flow_cli(
    query: str,
    flow_type: str,
    flow_options: Dict[str, Any],
    strategy_name: str,
    org_name: str,
    kb_name: str,
    username: str,
    **kwargs,
) -> str:
    display_loggger = logger()
    display_loggger.debug(f"The query is: [{query}]")
    # remove the quotes at the beginning and end of the query
    query = query.strip('"').strip("'").strip()

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}{flow_type}"
    history_manager = get_history_manager(context)

    org, kb, user = cli_utils.setup_org_kb_user(context, org_name, kb_name, username)
    org_name = org.name
    kb_name = kb.name
    kb_description = kb.description
    username = user.username

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org_name,
        kb_name=kb_name,
        username=username,
        strategy_name=strategy_name,
        flow_type=flow_type,
        flow_options=flow_options,
        kb_description=kb_description,
        ad_hoc_kb=True,
        display_logger=display_loggger,
    )

    chat_query_result = history_manager.run_query_item(
        org=exec_info.org,
        kb=exec_info.kb,
        user=exec_info.user,
        chat_query_item=exec_info.target_chat_query_item,
    )

    result_article = flow_utils.chat_query_result_to_article(query, chat_query_result)

    return result_article


@click.command(help="Run the flow for the query.")
@click.option(
    "-q",
    "--query",
    "query",
    required=False,
    default=None,
    help="The query for the flow. Required if not quering for options.",
)
@click.option(
    "-t",
    "--flow-type",
    "flow_type",
    type=str,
    required=False,
    default=FlowType.ANSWER.value,
    help="The flow type.",
)
@click.option(
    "-p",
    "--param",
    multiple=True,
    callback=parse_name_value,
    help="Specify a parameter as name=value. Can be used multiple times.",
)
@click.option(
    "-f",
    "--param-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to a file containing parameters as name=value pairs. The -p option can be used to override these parameters.",
)
@click.option(
    "-o",
    "--output-file",
    type=click.Path(exists=False, dir_okay=False, writable=True),
    required=False,
    default=None,
    help="Path to a file to save the output. Print to stdout if not specified.",
)
@click.option(
    "--strategy",
    "strategy_name",
    required=False,
    default=None,
    help="The strategy to use, default the default strategy.",
)
@click.option(
    "--info",
    "show_info",
    is_flag=True,
    help="Show the information such as function and options for the flow.",
)
@click.option(
    "--list",
    "list",
    is_flag=True,
    help="List all the available flows.",
)
@click.option(
    "--org",
    "org_name",
    default=None,
    required=False,
    help="The org to add the documents to.",
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
    help="The user to use, default the admin user.",
)
@common_options
def flow(
    query: str,
    flow_type: str,
    param: Dict[str, Any],
    param_file: click.Path,
    output_file: click.Path,
    strategy_name: str,
    show_info: bool,
    list: bool,
    org_name: str,
    kb_name: str,
    username: str,
    **kwargs,
) -> None:

    try:
        context = ContextManager().get_context()
        flow_manager = FlowManager(context.settings)

        if list:
            for name, flow_class in flow_manager.flow_classes.items():
                click.echo(f"{name:<15}: {flow_class.short_description()}")
            return

        if flow_type == "" or flow_type is None:
            flow_type = flow_manager.get_default_flow_type()
        flow = flow_manager.get_flow_by_type(flow_type)
        supported_flow_options = flow.get_flow_option_items()

        def _print_flow_info():
            click.echo(cli_utils.DELIM_LINE)
            click.echo(f"{flow_type}: {flow.short_description()}")
            click.echo(flow.full_description())
            click.echo(cli_utils.DELIM_LINE)
            click.echo(f"Use -p name=value to specify options for {flow_type}:\n")

            # sort the options by name
            foi_list = flow.get_flow_option_items()
            if foi_list is None or len(foi_list) == 0:
                return
            foi_list.sort(key=lambda x: x.name)
            for foi in foi_list:
                words = foi.description.split(" ")
                if foi.required:
                    words.append("[Required]")
                if foi.default_value is not None:
                    words.append(f"[default: {foi.default_value}]")

                if foi.flow_components:
                    for component_type, component_names in foi.flow_components.items():
                        words.append(
                            f"[{component_type.value}: {', '.join(component_names)}]"
                        )

                # split words into lines less than 100 characters
                common_width = 20
                desc = []
                cur_line = ""
                for word in words:
                    if (
                        len(cur_line) + len(word) + 3
                        > cli_utils.LINE_WIDTH - common_width
                    ):
                        desc.append(cur_line)
                        cur_line = word
                    else:
                        if cur_line:
                            cur_line += " " + word
                        else:
                            cur_line = word
                if cur_line:
                    desc.append(cur_line)

                name_len = len(foi.name)

                padding = " " * (common_width - name_len)
                indent = " " * (common_width + 2)

                if name_len <= common_width:
                    click.echo(f"{foi.name}{padding}: {desc[0]}")
                    start = 1
                else:
                    click.echo(f"{foi.name}:")
                    start = 0

                for line in desc[start:]:
                    click.echo(f"{indent}{line}")

        if show_info:
            _print_flow_info()
            return

        if query is None:
            click.echo("Input query is required by -q argument.\n", err=True)

            ctx = click.get_current_context()
            click.echo(ctx.get_help())
            return

        flow_options: Dict[str, Any] = {}

        # Load parameters from file
        if param_file:
            file_params = load_params_from_file(param_file)
            flow_options.update(file_params)

        # Load parameters from command line
        if param:
            flow_options.update(param)

        # check the parameters
        err_msgs = []
        warning_msgs = []
        supported_flow_options_dict = {foi.name: foi for foi in supported_flow_options}
        for item in flow_options:
            item_str = str(item)
            if item_str not in supported_flow_options_dict:
                err_msgs.append(f"Unsupported option: {item}")

        for foi in supported_flow_options:
            if foi.required and foi.name not in flow_options:
                err_msgs.append(f"Required option {foi.name} is missing.")

        if warning_msgs:
            for msg in warning_msgs:
                click.echo(f"[Parameter Warning] {msg}")

        if err_msgs:
            for msg in err_msgs:
                click.echo(f"[Parameter Error  ] {msg}", err=True)
            return

        logger().info(f"Loaded flow_options: {flow_options}")

        result_article = _run_flow_cli(**locals())

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result_article)
        else:
            click.echo(result_article)
    except Exception as e:
        click.echo(f"\nError: {e}\n\nUse -l DEBUG to see the details.\n", err=True)
        trace = traceback.format_exc()
        click.echo(f"{DELIM_LINE}\n", err=True)
        click.echo(f"{trace}", err=True)
        return
