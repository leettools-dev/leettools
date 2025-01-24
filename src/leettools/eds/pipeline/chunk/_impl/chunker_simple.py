import math
import re
from typing import List

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.utils.tokenizer import Tokenizer
from leettools.core.schemas.chunk import Chunk
from leettools.eds.pipeline.chunk.chunker import AbstractChunker
from leettools.settings import SystemSettings

HEADING_PATTERN = r"^\s*(#+) "
TABLE_PATTERN = r"^\s*\|"


class _ChunkState:
    # working states for a chunking process
    def __init__(self):
        self.chunks: List[Chunk] = []
        self.headings: List[str] = []
        self.postion_in_doc: List[int] = []
        self.chunk_content: str = ""
        self.non_table_content: str = ""
        self.line_is_in_table: bool = False
        self.start_offset: int = 0
        self.end_offset: int = 0
        self.is_first_line: bool = True
        self.visited_positions = set()

    def _get_headings_str(self) -> str:
        return " * ".join(self.headings)

    def _get_chunk_postion(self) -> str:
        return ".".join([str(x) for x in self.postion_in_doc])


class ChunkerSimple(AbstractChunker):
    """
    The simple chunker follows the following rules:
    1. The first line is always a heading.
    2. When we have to separate a table, we will copy the non-table content to
    the new chunk.
    """

    def __init__(self, settings: SystemSettings):
        """
        Initializes the ChunkerSimple class.
        """
        super().__init__()
        self.chunk_size = settings.DEFAULT_CHUNK_SIZE
        self.tokenizer = Tokenizer(settings)

    def _add_chunk(self, state: _ChunkState) -> None:
        parts = []
        if self._get_chunk_size(state.chunk_content) <= self.chunk_size:
            parts.append(state.chunk_content)
        else:
            parts = self._split_line(state.chunk_content)
        index = 1
        for part in parts:
            position = state._get_chunk_postion()
            if index > 0:
                position = f"{position}.{index}"
            if position in state.visited_positions:
                raise exceptions.UnexpectedCaseException(
                    f"Duplicate position: {position}"
                )
            new_chunk = Chunk(
                content=part,
                heading=state._get_headings_str(),
                position_in_doc=position,
                start_offset=state.start_offset,
                end_offset=state.end_offset,
            )
            state.visited_positions.add(position)
            state.chunks.append(new_chunk)  # Save the current chunk
            index += 1
        state.chunk_content = ""
        state.start_offset = state.end_offset

    def _get_chunk_size(self, text: str) -> int:
        return self.tokenizer.token_count(text)

    def _check_chunk_size(self, state: _ChunkState, line: str) -> None:
        combined_content = state.chunk_content + line
        if (
            self._get_chunk_size(combined_content) > self.chunk_size
            and len(state.chunk_content) > 0
        ):
            self._add_chunk(state)

            # for the new chunk, we add the non-table content if it exists
            if state.line_is_in_table:
                state.chunk_content = state.non_table_content
                state.chunk_content += line.strip() + "\n"
            else:
                state.chunk_content = line.strip() + "\n"
                state.non_table_content = line.strip() + "\n"

            heading_level = len(state.headings) + 1
            self._update_headings(state, "", heading_level)
        else:
            state.chunk_content += line.strip() + "\n"
            if not state.line_is_in_table:
                state.non_table_content += line.strip() + "\n"

    def _process_content(self, state: _ChunkState, content: str) -> List[Chunk]:
        state.line_is_in_table = False
        state.start_offset = 0
        state.end_offset = 0

        lines = content.split("\n")
        for line in lines:
            if len(line.strip()) == 0:
                state.end_offset += len(line) + 1
                continue
            if re.match(HEADING_PATTERN, line):  # If the line is a heading
                self._process_heading(state, line)
            elif re.match(TABLE_PATTERN, line):
                self._process_table(state, line)
            else:
                self._process_normal_line(state, line)
            state.end_offset += len(line) + 1

        # Don't forget the last chunk
        if state.chunk_content:
            self._add_chunk(state)

        return state.chunks

    def _process_heading(self, state: _ChunkState, line: str) -> None:
        state.line_is_in_table = False
        if len(state.chunk_content) > 0:
            self._add_chunk(state)

        if state.is_first_line:
            state.is_first_line = False

        # update the headings and position
        heading_level = len(re.match(HEADING_PATTERN, line).group(1))
        heading_content = re.sub(HEADING_PATTERN, "", line)
        state.non_table_content = line.strip() + "\n"
        self._update_headings(state, heading_content.strip(), heading_level)

    def _process_normal_line(self, state: _ChunkState, line: str) -> None:
        if state.is_first_line:
            heading_level = 1
            heading_content = line.strip()
            self._update_headings(state, heading_content, heading_level)
            state.is_first_line = False
        state.line_is_in_table = False
        self._check_chunk_size(state, line)

    def _process_table(self, state: _ChunkState, line: str) -> None:
        if not state.line_is_in_table:  # Start of a new table
            state.line_is_in_table = True  # Set flag to indicate we're in a table
        self._check_chunk_size(state, line)

    def _split_line(self, line: str) -> List[str]:
        """
        Split the line into smaller chunks each fits the chunk size
        """
        num_tokens = self._get_chunk_size(line)
        if num_tokens % self.chunk_size == 0:
            num_parts = int(num_tokens / self.chunk_size)
        else:
            num_parts = math.floor(num_tokens / self.chunk_size) + 1
        return self.tokenizer.split_text(line, num_parts)

    def _update_headings(
        self, state: _ChunkState, heading_content: str, heading_level: int
    ) -> None:
        if len(state.headings) >= heading_level:
            while len(state.headings) > heading_level:
                state.headings.pop()
                state.postion_in_doc.pop()

            state.headings[-1] = heading_content
            state.postion_in_doc[-1] += 1
        else:
            # If the heading level is greater than the current heading level
            while len(state.headings) < heading_level - 1:
                state.headings.append("")
                state.postion_in_doc.append(0)
            state.headings.append(heading_content)
            state.postion_in_doc.append(1)

    def chunk(self, text: str) -> List[Chunk]:
        """
        Processes the markdown content and returns a list of chunks.
        """
        state = _ChunkState()
        return self._process_content(state, text)


if __name__ == "__main__":
    import sys

    settings = SystemSettings().initialize()
    chunker = ChunkerSimple(settings)
    input_file = sys.argv[1]
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    chunks: List[Chunk] = chunker.chunk(text)
    for chunk in chunks:
        print("Heading: ", chunk.heading)
        print("Position: ", chunk.position_in_doc)
        print("Content: ", chunk.content)
        print("Start Offset: ", chunk.start_offset)
        print("End Offset: ", chunk.end_offset)
        print("-" * 20 + "\n")
        # extract the chunk content from the original text by using offsets
        print(text[chunk.start_offset : chunk.end_offset])
        print("#" * 20 + "\n")
