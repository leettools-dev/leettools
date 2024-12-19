from pathlib import Path

import click

from leettools.cli.parser.parser_base import convert_to_markdown, get_parser_options


@click.command()
@click.pass_context
def pptx2md(ctx, input: Path, output: Path, parser_type: str | None, force: bool):
    """Convert PPTX file to Markdown format."""
    # check if input is a pptx file
    if not input.suffix.lower() == ".pptx":
        raise click.ClickException("Input file must be a PPTX file")

    used_parser = convert_to_markdown(input, output, parser_type, force)
    click.echo(
        f"Successfully converted {input} to {output} using {used_parser or 'default'} parser"
    )


# Apply common options
for option in get_parser_options():
    pptx2md = option(pptx2md)

if __name__ == "__main__":
    pptx2md()
