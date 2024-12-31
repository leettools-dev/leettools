import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from leettools.common.logging import EventLogger
from leettools.core.repo._impl.duckdb.vector_store_dense_duckdb import (
    VectorStoreDuckDBDense,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.eds.str_embedder.dense_embedder import AbstractDenseEmbedder
from leettools.eds.str_embedder.schemas.schema_dense_embedder import DenseEmbeddings


@pytest.fixture(scope="session", autouse=True)
def test_db_path():
    """Create and manage test database directory."""
    test_db_path = Path("tests/data/test_db")
    test_db_path.mkdir(parents=True, exist_ok=True)
    yield test_db_path
    # Cleanup after all tests in the session are complete
    for file in test_db_path.glob("*.db"):
        try:
            file.unlink()
        except PermissionError:
            pass  # Handle case where file is still in use


@pytest.fixture
def context(test_db_path):
    """Create a mock context for testing."""
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.settings.DUCKDB_PATH = str(test_db_path)
    context.settings.DUCKDB_FILE = "test_vectors.db"
    return context


@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests."""
    EventLogger.set_global_default_level("DEBUG")


@pytest.fixture
def vector_store(context):
    """Create an instance of VectorStoreDuckDBDense."""
    return VectorStoreDuckDBDense(context)


@pytest.fixture
def org():
    """Create a test organization."""
    return Org(org_id="test_org_id", name="Test Org", description="A test organization")


@pytest.fixture()
def test_kb_identifier() -> str:
    return f"test_kbid_{str(uuid.uuid4())}"


@pytest.fixture
def kb(test_kb_identifier: str):
    """Create a test knowledge base."""
    return KnowledgeBase(name="test_kb", kb_id=test_kb_identifier)


@pytest.fixture
def user():
    """Create a test user."""
    return User(user_uuid="test_user_uuid", username="test_username")


@pytest.fixture
def segment(test_kb_identifier: str):
    """Create a test segment."""
    return Segment(
        segment_uuid="test_segment_uuid",
        document_uuid="test_doc_id",
        content="This is a test segment.",
        doc_uri="test_doc_uri",
        kb_id=test_kb_identifier,
        position_in_doc="1",
        docsource_uuid="test_docsource_uuid",
        docsink_uuid="test_docsink_uuid",
    )


@pytest.fixture
def local_embedder():
    """Create a mock local embedder."""


def test_save_segments(vector_store, org, kb, user, segment):
    """Test saving a list of segments."""

    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        vector_store.save_segments(org, kb, user, [segment])

        # Verify that the segment vector was created
        result = vector_store.get_segment_vector(org, kb, segment.segment_uuid)
        expected = vector_store._normalize_vector([0.1, 0.2, 0.3])
        for i in range(len(expected)):
            # check if the result is within 1e-6 of the expected value
            assert round(result[i], 6) == round(expected[i], 6)


def test_update_segment_vector(vector_store, org, kb, user, segment):
    """Test updating a segment vector."""
    # Mock the embedder returned by get_dense_embedder_for_kb
    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3

    # Patch the get_dense_embber_for_kb function in the correct module
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        # Create the segment vector with the mock embedder
        vector_store.save_segments(org, kb, user, [segment])

        # Update the segment
        segment.content = "Updated content."
        mock_embedder.embed.return_value = DenseEmbeddings(
            dense_embeddings=[[0.4, 0.5, 0.6]]
        )

        # Call the update method
        vector_store.update_segment_vector(org, kb, user, segment)

        # Verify that the segment vector was updated
        result = vector_store.get_segment_vector(org, kb, segment.segment_uuid)
        expected = vector_store._normalize_vector([0.4, 0.5, 0.6])
        for i in range(len(expected)):
            # check if the result is within 1e-6 of the expected value
            assert round(result[i], 6) == round(expected[i], 6)


def test_delete_segment_vector(vector_store, org, kb, user, segment):
    """Test deleting a segment vector."""
    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        vector_store.save_segments(org, kb, user, [segment])

        # Delete the segment vector
        assert vector_store.delete_segment_vector(org, kb, segment.segment_uuid) is True

        # Verify that the segment vector no longer exists
        result = vector_store.get_segment_vector(org, kb, segment.segment_uuid)
        assert result == []


def test_search_in_kb(vector_store, org, kb, user, segment):
    """Test searching for segments in the knowledge base."""
    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        vector_store.save_segments(org, kb, user, [segment])

        # Mock the search parameters
        query = "test segment"
        top_k = 5
        results = vector_store.search_in_kb(org, kb, user, query, top_k)

        # Verify that the search returns results
        assert len(results) > 0
        assert results[0].segment_uuid == segment.segment_uuid

        filter_expr = f"{Segment.FIELD_DOCSOURCE_UUID}='{segment.docsource_uuid}'"
        results = vector_store.search_in_kb(
            org, kb, user, query, top_k, filter_expr=filter_expr
        )
        assert len(results) > 0
        assert results[0].segment_uuid == segment.segment_uuid

        # test full text search
        vector_store.rebuild_full_text_index(org, kb, user)
        results = vector_store.full_text_search_in_kb(org, kb, user, query, top_k)
        assert len(results) > 0
        assert results[0].segment_uuid == segment.segment_uuid


def test_get_segment_vector_not_found(vector_store, org, kb, user, segment):
    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        vector_store.save_segments(org, kb, user, [segment])

        # Test getting a segment vector that does not exist.
        result = vector_store.get_segment_vector(org, kb, "non_existent_uuid")
        assert result == []


def test_delete_segment_vector_not_found(vector_store, org, kb, user, segment):
    """Test deleting a segment vector that does not exist."""
    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        vector_store.save_segments(org, kb, user, [segment])

        # Test deleting a segment vector that does not exist.
        result = vector_store.delete_segment_vector(org, kb, "non_existent_uuid")
        assert result is True  # Should return True even if it doesn't exist


def test_delete_segment_vectors_by_docsink_uuid(vector_store, org, kb, user, segment):
    """Test deleting segment vectors by docsink UUID."""
    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        vector_store.save_segments(org, kb, user, [segment])
        # Call the delete method
        result = vector_store.delete_segment_vectors_by_docsink_uuid(
            org, kb, segment.docsink_uuid
        )

    # Verify that the segment vector was deleted
    assert result is True
    assert vector_store.get_segment_vector(org, kb, segment.segment_uuid) == []


def test_delete_segment_vectors_by_docsource_uuid(vector_store, org, kb, user, segment):
    """Test deleting segment vectors by docsource UUID."""
    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        vector_store.save_segments(org, kb, user, [segment])

        # Call the delete method
        result = vector_store.delete_segment_vectors_by_docsource_uuid(
            org, kb, segment.docsource_uuid
        )

        # Verify that the segment vector was deleted
        assert result is True
        assert vector_store.get_segment_vector(org, kb, segment.segment_uuid) == []


def test_delete_segment_vectors_by_document_id(vector_store, org, kb, user, segment):
    """Test deleting segment vectors by document ID."""
    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        vector_store.save_segments(org, kb, user, [segment])

        # Call the delete method
        result = vector_store.delete_segment_vectors_by_document_id(
            org, kb, segment.document_uuid
        )

        # Verify that the segment vector was deleted
        assert result is True
        assert vector_store.get_segment_vector(org, kb, segment.segment_uuid) == []


def test_get_segment_vector(vector_store, org, kb, user, segment):
    """Test getting a segment vector."""
    mock_embedder = MagicMock(spec=AbstractDenseEmbedder)
    mock_embedder.embed.return_value = DenseEmbeddings(
        dense_embeddings=[[0.1, 0.2, 0.3]]
    )
    mock_embedder.get_dimension.return_value = 3
    with patch(
        "leettools.core.repo._impl.duckdb.vector_store_dense_duckdb.create_dense_embedder_for_kb",
        return_value=mock_embedder,
    ):
        vector_store.save_segments(org, kb, user, [segment])

        # Call the get method
        result = vector_store.get_segment_vector(org, kb, segment.segment_uuid)

        # Verify that the correct segment vector is returned
        expected = vector_store._normalize_vector([0.1, 0.2, 0.3])
        for i in range(len(expected)):
            # check if the result is within 1e-6 of the expected value
            assert round(result[i], 6) == round(expected[i], 6)
