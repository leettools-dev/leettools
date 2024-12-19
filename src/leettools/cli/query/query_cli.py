import click

from .query_get import get
from .query_get_article_md import get_article_md
from .query_list import list
from .query_run import run
from .query_section_add import section_add
from .query_section_regen import section_regen
from .query_section_remove import section_remove
from .query_section_set import section_set


@click.group()
def query():
    """
    Run new queries or get information about existing queries.
    """
    pass


query.add_command(list)
query.add_command(get)
query.add_command(run)
query.add_command(get_article_md)
query.add_command(section_set)
query.add_command(section_regen)
query.add_command(section_add)
query.add_command(section_remove)
