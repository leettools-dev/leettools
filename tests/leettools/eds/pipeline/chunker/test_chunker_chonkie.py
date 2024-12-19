from unittest.mock import Mock, patch

import pytest

from leettools.core.schemas.chunk import Chunk
from leettools.eds.pipeline.chunk._impl.chunker_chonkie import ChonkieChunker
from leettools.settings import SystemSettings


@pytest.fixture
def settings():
    """Fixture for system settings"""
    settings = SystemSettings().initialize()
    settings.DEFAULT_CHUNK_SIZE = 128
    settings.DEFAULT_CHUNK_OVERLAP = 32
    return settings


@pytest.fixture
def mock_chonkie_chunk():
    """Fixture for mocked Chonkie chunk"""
    return Mock(text="Test chunk content", start_index=0, end_index=10)


@pytest.fixture
def chunker(settings):
    """Fixture for ChonkieChunker instance"""
    return ChonkieChunker(settings)


class TestChonkieChunker:
    def test_init(self, settings: SystemSettings):
        """Test chunker initialization"""
        chunker = ChonkieChunker(settings)
        assert chunker.settings == settings
        assert chunker.chunker.chunk_size == settings.DEFAULT_CHUNK_SIZE
        assert chunker.chunker.chunk_overlap == settings.DEFAULT_CHUNK_OVERLAP

    def test_convert_to_chunk(self, chunker, mock_chonkie_chunk):
        """Test conversion from Chonkie chunk to our Chunk schema"""
        result = chunker._convert_to_chunk(mock_chonkie_chunk, 0)

        assert isinstance(result, Chunk)
        assert result.content == "Test chunk content"
        assert result.heading == "Chunk 1"
        assert result.position_in_doc == "0"
        assert result.start_offset == 0
        assert result.end_offset == 10

    @patch("chonkie.TokenChunker.__call__")
    def test_chunking_with_mock(self, mock_call, chunker, mock_chonkie_chunk):
        """Test chunking with mocked Chonkie chunker"""
        mock_call.return_value = [mock_chonkie_chunk]

        result = chunker.chunk("Test text")

        assert len(result) == 1
        chunk = result[0]
        assert isinstance(chunk, Chunk)
        assert chunk.content == "Test chunk content"
        assert chunk.heading == "Chunk 1"
        assert chunk.position_in_doc == "0"
        assert chunk.start_offset == 0
        assert chunk.end_offset == 10

    def test_chunking_empty_text(self, chunker):
        """Test chunking with empty text"""
        result = chunker.chunk("")
        assert result == []

    def test_chunking_with_actual_text(self, chunker):
        """Test chunking with actual text input"""
        text = "This is a test text that should be chunked into smaller pieces."
        result = chunker.chunk(text)

        assert len(result) > 0
        for i, chunk in enumerate(result):
            assert isinstance(chunk, Chunk)
            assert chunk.content  # Check content is not empty
            assert chunk.heading == f"Chunk {i + 1}"
            assert chunk.position_in_doc == str(i)
            assert isinstance(chunk.start_offset, int)
            assert isinstance(chunk.end_offset, int)
            assert chunk.start_offset < chunk.end_offset
