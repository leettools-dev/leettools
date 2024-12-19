from typing import List

from chonkie import Chunk as ChonkieChunk
from chonkie import TokenChunker as ChonkieTokenChunker

from leettools.core.schemas.chunk import Chunk
from leettools.eds.pipeline.chunk.chunker import AbstractChunker
from leettools.settings import SystemSettings


class ChonkieChunker(AbstractChunker):
    """
    Chunker implementation using Chonkie's TokenChunker.
    """

    def __init__(self, settings: SystemSettings):
        """Initialize the chunker with system settings.

        Args:
            settings: SystemSettings containing chunking configuration
        """
        self.settings = settings
        self.chunker = ChonkieTokenChunker(
            chunk_size=settings.DEFAULT_CHUNK_SIZE,
            chunk_overlap=settings.DEFAULT_CHUNK_OVERLAP,
        )

    def _convert_to_chunk(self, chonkie_chunk: ChonkieChunk, index: int) -> Chunk:
        """Convert Chonkie chunk to our Chunk schema.

        Args:
            chonkie_chunk: Chunk from Chonkie
            index: Position of the chunk in the sequence

        Returns:
            Chunk object in our schema
        """
        return Chunk(
            content=chonkie_chunk.text,
            heading=f"Chunk {index + 1}",
            position_in_doc=str(index),
            start_offset=chonkie_chunk.start_index,
            end_offset=chonkie_chunk.end_index,
        )

    def chunk(self, text: str) -> List[Chunk]:
        """
        Chunk the text using Chonkie's TokenChunker.

        Args:
            text: The text to chunk.

        Returns:
            List of Chunk objects containing the chunked text.
        """
        chonkie_chunks: List[ChonkieChunk] = self.chunker(text)
        return [
            self._convert_to_chunk(chunk, i) for i, chunk in enumerate(chonkie_chunks)
        ]
