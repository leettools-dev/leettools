from pathlib import Path

import click

from leettools.cli.parser.parser_base import convert_to_markdown, get_parser_options


@click.command()
@click.pass_context
def docx2md(ctx, input: Path, output: Path, parser_type: str | None, force: bool):
    """Convert DOCX file to Markdown format."""
    # check if input is a docx file
    if not input.suffix.lower() == ".docx":
        raise click.ClickException("Input file must be a DOCX file")

    used_parser = convert_to_markdown(input, output, parser_type, force)
    click.echo(
        f"Successfully converted {input} to {output} using {used_parser or 'default'} parser"
    )


# Apply common options
for option in get_parser_options():
    docx2md = option(docx2md)

if __name__ == "__main__":
    docx2md()
