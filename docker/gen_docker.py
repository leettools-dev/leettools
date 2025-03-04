"""
This program reads the requirements.txt file and generates a Dockerfile.
"""

import os
from typing import Dict, List

import click
import jinja2


def parse_requirements(file_path: str) -> Dict[str, List[str]]:
    categories: Dict[str, List[str]] = {}
    current_category: str = None

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("#"):
                current_category = line[1:].strip().lower()
                categories[current_category] = []
            if "#" in line:
                line = line.split("#")[0].strip()
                if line == "":
                    continue
                else:
                    categories[current_category].append(line)
            elif line and current_category:
                categories[current_category].append(line)

    return categories


def generate_dockerfile(
    template_file: str, output_path: str, categories: Dict[str, List[str]]
):
    # Setup Jinja2 environment

    template_path = os.path.dirname(template_file)
    template_name = os.path.basename(template_file)

    templateLoader = jinja2.FileSystemLoader(searchpath=template_path)
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(template_name)

    # Render the template with the categories dictionary
    output_text = template.render(categories=categories)

    # Write the output to the Dockerfile
    with open(output_path, "w") as file:
        file.write(output_text)
    print(f"Dockerfile has been generated in {output_path}")


@click.command()
@click.option(
    "-t",
    "--type",
    "type",
    default="prod",
    required=False,
    help="The type of the template file to use (prod or dev).",
)
@click.option(
    "-o",
    "--output",
    "output_filename",
    default="Dockerfile",
    required=False,
    help="Output file name relative to the root dir, default to Dockerfile.",
)
def run(type: str, output_filename: str) -> None:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))

    requirements_file = os.path.join(root_dir, "requirements.txt")
    template_file = os.path.join(script_dir, f"Dockerfile.{type}.template")

    if not os.path.exists(template_file):
        print(f"Template file {template_file} does not exist.")
        return

    output_file = os.path.join(root_dir, output_filename)

    categories = parse_requirements(requirements_file)

    generate_dockerfile(template_file, output_file, categories)


if __name__ == "__main__":
    run()
