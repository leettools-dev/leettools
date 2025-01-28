import click

from .kb_add_local import add_local
from .kb_add_search import add_search
from .kb_add_url import add_url
from .kb_add_url_list import add_url_list
from .kb_create import create
from .kb_info import info
from .kb_ingest import ingest
from .kb_list import list
from .kb_list_db import list_db


@click.group()
def kb():
    """
    Knowledge base management.
    """
    pass


kb.add_command(list)
kb.add_command(list_db)
kb.add_command(add_local)
kb.add_command(add_search)
kb.add_command(add_url_list)
kb.add_command(add_url)
kb.add_command(create)
kb.add_command(ingest)
kb.add_command(info)
