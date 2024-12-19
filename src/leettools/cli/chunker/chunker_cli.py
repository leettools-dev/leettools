import click

from .chunker_text2chunks import text2chunks


@click.group()
def chunker():
    """Chunker commands."""
    pass


chunker.add_command(text2chunks)
