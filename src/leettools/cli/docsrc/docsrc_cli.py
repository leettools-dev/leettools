import click

from .docsrc_ingest import ingest
from .docsrc_list import list


@click.group()
def docsrc():
    """
    DocSource management.
    """
    pass


docsrc.add_command(list)
docsrc.add_command(ingest)
