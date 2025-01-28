import importlib
import traceback
from pathlib import Path

import click

from leettools.cli.chunker import chunker_cli
from leettools.cli.doc import doc_cli
from leettools.cli.docsink import docsink_cli
from leettools.cli.docsrc import docsrc_cli
from leettools.cli.flow import flow_cli
from leettools.cli.kb import kb_cli
from leettools.cli.llm import llm_cli
from leettools.cli.options_common import common_options
from leettools.cli.parser import parser_cli
from leettools.cli.query import query_cli
from leettools.common import exceptions
from leettools.context_manager import Context


@click.group(name="edscmd")
@common_options
def run(**kwargs):
    """
    Commad line tools for leettools system.
    """
    pass


@run.command()
def list():
    """
    List all CLI commands and subcommands.
    """

    def _tabs(layer: int) -> str:
        return "\t" * layer

    def _list_all_commands(subcommand: click.Command, layer: int) -> None:
        if layer == 0:
            padding = 0
        else:
            padding = 20

        if not isinstance(subcommand, click.Group):
            help_str = subcommand.help.strip()
            command_str = str(subcommand).strip()
            print(f"{_tabs(layer)}{command_str:<{padding}}\t{help_str}")
            return
        commands = subcommand.commands
        for subcommand_name, subcommand in commands.items():
            if subcommand.help is None:
                help_str = ""
            else:
                help_str = subcommand.help.strip()
            command_str = subcommand_name.strip()
            print(f"{_tabs(layer)}{command_str:<{padding}}\t{help_str}")
            if isinstance(subcommand, click.Group):
                _list_all_commands(subcommand, layer + 1)

    _list_all_commands(run, 0)


run.add_command(doc_cli.doc)
run.add_command(docsink_cli.docsink)
run.add_command(docsrc_cli.docsrc)
run.add_command(query_cli.query)
run.add_command(kb_cli.kb)
run.add_command(llm_cli.llm)
run.add_command(parser_cli.parser)
run.add_command(chunker_cli.chunker)
run.add_command(flow_cli.flow)


def _add_extension_cli(context: Context):
    from leettools.common.utils import module_utils

    settings = context.settings
    extension_cli_path = Path(f"{settings.EXTENSION_PATH}/cli")
    if extension_cli_path.exists():
        cli_ext_module_name = module_utils.generate_package_name(
            base_path=settings.CODE_ROOT_PATH, package_path=extension_cli_path
        )
        # import extension cli defined in __init__.py in the extension cli folder
        extension_pkg = importlib.import_module(cli_ext_module_name)
        if hasattr(extension_pkg, "__all__"):
            for command_name in extension_pkg.__all__:
                command = getattr(extension_pkg, command_name, None)
                if command is not None:
                    run.add_command(command)


def main():
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = context.EDS_CLI_CONTEXT_PREFIX

    _add_extension_cli(context)
    try:
        run()
    except exceptions.EdsExceptionBase as leettools_exception:
        errmsg = leettools_exception.exception_message
        stack_trace = traceback.format_exc()

        # Print the header
        click.secho("=" * 40, fg="cyan", bold=True)
        click.secho(f" ERROR: {errmsg} ", fg="red", bold=True)
        click.secho("=" * 40, fg="cyan", bold=True)

        # Print the stack trace
        click.secho(stack_trace, fg="yellow")
    finally:
        # Add any cleanup code here
        pass


if __name__ == "__main__":
    main()
