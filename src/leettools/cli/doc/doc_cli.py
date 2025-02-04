import click

from .doc_list import list
from .doc_list_all_segments import list_all_segements
from .doc_list_segments import list_segments_for_doc
from .doc_print import print
from .doc_remove import remove
from .doc_summarize import summarize_all


@click.group()
def doc():
    """
    Document management.
    """
    pass


doc.add_command(list_segments_for_doc)
doc.add_command(list_all_segements)
doc.add_command(summarize_all)
doc.add_command(list)
doc.add_command(print)
doc.add_command(remove)
