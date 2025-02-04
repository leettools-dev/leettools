import click

from .docsink_list import list
from .docsink_remove import remove


@click.group()
def docsink():
    """
    DocSink management.
    """
    pass


docsink.add_command(list)
docsink.add_command(remove)
