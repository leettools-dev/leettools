import click

from .docsink_list import list


@click.group()
def docsink():
    """
    DocSink management.
    """
    pass


docsink.add_command(list)
