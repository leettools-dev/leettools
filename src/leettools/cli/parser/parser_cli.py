import click

from .parser_pdf2md import pdf2md
from .parser_docx2md import docx2md
from .parser_pptx2md import pptx2md


@click.group()
def parser():
    """Parser commands."""
    pass


parser.add_command(pdf2md)
parser.add_command(docx2md)
parser.add_command(pptx2md)
