import click

from .llm_inference import inference


@click.group()
def llm():
    """
    Run llm commands directly.
    """
    pass


llm.add_command(inference)
