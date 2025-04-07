import click

from .strat_list import list


@click.group()
def strategy():
    """
    Manage the strategies.
    """
    pass


strategy.add_command(list)
