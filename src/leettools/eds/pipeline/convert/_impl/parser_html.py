""" Module to convert HTML to Markdown. """

import click
import markdownify
from bs4 import BeautifulSoup
from pydantic import BaseModel

from leettools.common.logging import logger


class ParserHTML(BaseModel):
    """Class to parse HTML content and convert it to Markdown."""

    def parse_html_content(self, html_content: str) -> str:
        """
        Parses the HTML content and returns the meaningful
        text content in Markdown format.

        Args:
            html_content: The HTML content to be parsed.

        Returns:
            The meaningful text content in Markdown format.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text(separator="\n", strip=True)
        logger().debug(f"Text content from soup: {text_content}")

        meaningful_content = self._filter_and_group_paragraphs_with_headings(
            text_content
        )
        return meaningful_content

    def html2md(self, file_path: str) -> str:
        """
        Parses the HTML file and returns the meaningful
        text content in Markdown format.

        Args:
            file_path: The path to the HTML file to be parsed.

        Returns:
            The meaningful text content in Markdown format.
        """

        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        result = markdownify.markdownify(html_content, heading_style="ATX")
        return result

        # right now we do not need to parse the html content manually
        # return self.parse_html_content(html_content)

    def _filter_and_group_paragraphs_with_headings(self, text: str) -> str:
        """
        Filters the meaningful paragraphs and groups them with headings.

        Args:
            text: The text content to be filtered and grouped.

        Returns:
            The meaningful paragraphs grouped with headings.
        """
        lines = text.split("\n")
        paragraphs = []
        current_paragraph = []
        paragraph_number = 0  # To keep track of paragraph numbering

        for line in lines:
            if (
                # TODO: This logic needs to be improved
                len(line.split())
                > 3
            ):  # Consider lines with more than 3 words as meaningful
                current_paragraph.append(line)
            elif current_paragraph:
                # Join the lines in the current paragraph
                joined_paragraph = " ".join(current_paragraph)
                if paragraph_number == 0:  # First paragraph as the title
                    paragraphs.append(f"# {joined_paragraph}")
                    paragraphs.append("## Content")
                else:  # Numbered headings for subsequent paragraphs
                    paragraphs.append(f"{joined_paragraph}")
                paragraph_number += 1
                current_paragraph = (
                    []
                )  # Start a new paragraph for the next set of meaningful lines

        # Ensure the last paragraph is added if it wasn't ended by a short line
        if current_paragraph:
            joined_paragraph = " ".join(current_paragraph)
            if paragraph_number == 0:
                paragraphs.append(f"# {joined_paragraph}")
                paragraphs.append("## Content")
            else:
                paragraphs.append(f"{joined_paragraph}")

        return "\n\n".join(paragraphs)


@click.command()
@click.option(
    "-i",
    "--input_file",
    "input_file",
    required=True,
    help="The input html file.",
)
@click.option(
    "-o",
    "--output_file",
    "output_file",
    required=True,
    help="The output markdown file.",
)
def parse_html(input_file: str, output_file: str) -> None:
    parser = ParserHTML()
    markdown_content = parser.html2md(input_file)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)


# Example usage
if __name__ == "__main__":
    parse_html()
