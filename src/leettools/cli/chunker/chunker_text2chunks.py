from pathlib import Path

import click

from leettools.cli.chunker.chunker_base import convert_to_chunks, get_chunker_options


@click.command()
@click.pass_context
def text2chunks(ctx, input: Path, output: Path, chunker_type: str | None, force: bool):
    """Convert text file to chunks."""
    # Check if input is a text file
    if not input.suffix.lower() in [".md"]:
        raise click.ClickException("Input file must be a markdown file (.md)")

    used_chunker = convert_to_chunks(input, output, chunker_type, force)
    click.echo(
        f"Successfully chunked {input} to {output} using {used_chunker or 'default'} chunker"
    )


# Apply common options
for option in get_chunker_options():
    text2chunks = option(text2chunks)

if __name__ == "__main__":
    text2chunks()
