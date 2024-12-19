from pathlib import Path

import click

from leettools.context_manager import ContextManager
from leettools.eds.pipeline.convert.parser import create_parser


def get_parser_options():
    """Common Click options for all parser commands."""
    options = [
        click.option(
            "--input",
            "-i",
            type=click.Path(exists=True, path_type=Path),
            required=True,
            help="Path to the input file",
        ),
        click.option(
            "--output",
            "-o",
            type=click.Path(path_type=Path),
            required=True,
            help="Path where the markdown file will be saved",
        ),
        click.option(
            "--parser-module",
            "-p",
            type=str,
            default=None,
            help="Parser to use for conversion, usually the module name",
        ),
        click.option(
            "--force", "-f", is_flag=True, help="Overwrite output file if it exists"
        ),
    ]
    return options


def convert_to_markdown(
    input: Path, output: Path, parser_module: str | None, force: bool = False
) -> str:
    """Common conversion logic for different file types to Markdown."""
    if output.exists() and not force:
        raise click.ClickException(
            f"Output file {output} already exists. Use --force to overwrite."
        )

    context = ContextManager().get_context()
    settings = context.settings

    if parser_module is None:
        parser_module = settings.DEFAULT_PARSER

    parser = create_parser(settings, parser_module)
    markdown_content = parser.file2md(str(input))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_content)

    return parser_module
