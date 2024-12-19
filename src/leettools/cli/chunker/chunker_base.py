from pathlib import Path
from typing import List

import click

from leettools.context_manager import ContextManager
from leettools.core.schemas.chunk import Chunk
from leettools.eds.pipeline.chunk.chunker import create_chunker


def get_chunker_options():
    """Common Click options for all chunker commands."""
    options = [
        click.option(
            "--input",
            "-i",
            type=click.Path(exists=True, path_type=Path),
            required=True,
            help="Path to the input text file",
        ),
        click.option(
            "--output",
            "-o",
            type=click.Path(path_type=Path),
            required=True,
            help="Path where the chunks will be saved",
        ),
        click.option(
            "--chunker-name",
            "-c",
            type=str,
            default=None,
            help="Chunker module name to use for chunking",
        ),
        click.option(
            "--force", "-f", is_flag=True, help="Overwrite output file if it exists"
        ),
    ]
    return options


def convert_to_chunks(
    input: Path, output: Path, chunker_name: str | None, force: bool = False
):
    """Common chunking logic for text files."""
    if output.exists() and not force:
        raise click.ClickException(
            f"Output file {output} already exists. Use --force to overwrite."
        )

    context = ContextManager().get_context()
    settings = context.settings

    chunker = create_chunker(settings, chunker_name)
    text = input.read_text()
    chunks: List[Chunk] = chunker.chunk(text)

    # Create output directory if it doesn't exist
    output.parent.mkdir(parents=True, exist_ok=True)

    # Write chunks to output file
    with output.open("w") as f:
        for chunk in chunks:
            f.write(f"--- {chunk.heading} ---\n")
            f.write(f"position_in_doc: {chunk.position_in_doc}\n")
            f.write(f"start_offset: {chunk.start_offset}\n")
            f.write(f"end_offset: {chunk.end_offset}\n\n")
            f.write(f"{chunk.content}\n\n")

    return
