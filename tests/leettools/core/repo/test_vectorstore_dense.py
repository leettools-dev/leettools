import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from leettools.common.logging import EventLogger, logger
from leettools.common.temp_setup import TempSetup
from leettools.common.utils import time_utils
from leettools.context_manager import Context
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.repo._impl.duckdb.vector_store_dense_duckdb import (
    VectorStoreDuckDBDense,
)
from leettools.core.repo.vector_store import create_vector_store_dense
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSource, DocSourceCreate
from leettools.core.schemas.document import DocumentCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment, SegmentCreate
from leettools.core.schemas.user import User
from leettools.eds.rag.search.filter import BaseCondition, Filter
from leettools.eds.str_embedder.dense_embedder import AbstractDenseEmbedder
from leettools.eds.str_embedder.schemas.schema_dense_embedder import DenseEmbeddings
from leettools.settings import preset_store_types_for_tests


def test_vectorstore_dense():
    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        ds_create = DocSourceCreate(
            org_id=org.org_id,
            kb_id=kb.kb_id,
            source_type=DocSourceType.FILE,
            uri="doc_source_uri_001",
        )

        ds = (
            context.get_repo_manager()
            .get_docsource_store()
            .create_docsource(org, kb, ds_create)
        )

        try:
            _test_save_segments(context, org, kb, user, ds)
            _test_update_segment_vector(context, org, kb, user, ds)
            _test_delete_segment_vector(context, org, kb, user, ds)
            _test_search_in_kb(context, org, kb, user, ds)
            _test_get_segment_vector_not_found(context, org, kb, user, ds)
            _test_delete_segment_vector_not_found(context, org, kb, user, ds)
            _test_delete_segment_vectors_by_docsink_uuid(context, org, kb, user, ds)
            _test_delete_segment_vectors_by_docsource_uuid(context, org, kb, user, ds)
            _test_delete_segment_vectors_by_document_id(context, org, kb, user, ds)
            _test_get_segment_vector(context, org, kb, user, ds)
            logger().info("test_vectorstore_dense passed")
        finally:
            repo_manager = context.get_repo_manager()
            segstore = repo_manager.get_segment_store()
            for segment in segstore.get_segments_for_docsource(org, kb, ds):
                segstore.delete_segment(org, kb, segment)
            temp_setup.clear_tmp_org_kb_user(org, kb, user)


def _create_segment(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    docsource: DocSource,
    content: str,
) -> Segment:
    repo_manager = context.get_repo_manager()
    segstore = repo_manager.get_segment_store()
    original_uri = "original_uri1"
    raw_doc_uri = "raw_uri1"

    docsink_create = DocSinkCreate(
        docsource=docsource,
        original_doc_uri=original_uri,
        raw_doc_uri=raw_doc_uri,
    )
    docsink = repo_manager.get_docsink_store().create_docsink(org, kb, docsink_create)

    docsink_uuid = docsink.docsink_uuid

    document_create = DocumentCreate(
        content=content,
        doc_uri=raw_doc_uri,
        docsink=docsink,
    )
    document = repo_manager.get_document_store().create_document(
        org, kb, document_create
    )
    document_uuid = document.document_uuid

    epoch_time_ms = time_utils.cur_timestamp_in_ms()
    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=raw_doc_uri,
        docsink_uuid=docsink_uuid,
        kb_id=kb.kb_id,
        content=content,
        position_in_doc="1",
        original_uri=original_uri,
        created_timestamp_in_ms=epoch_time_ms,
        label_tag=str(epoch_time_ms),
    )
    segment = segstore.create_segment(org, kb, segment_create)
    assert segment.segment_uuid is not None
    return segment


def _test_save_segments(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test saving a list of segments."""
    vector_store = create_vector_store_dense(context)
    segment = _create_segment(
        context, org, kb, docsource, f"test content {uuid.uuid4()}"
    )

    vector_store.save_segments(org, kb, user, [segment])

    # Verify that the segment vector was created
    result = vector_store.get_segment_vector(org, kb, segment.segment_uuid)
    assert result is not None
    assert len(result) > 0
    for i in range(len(result)):
        if abs(result[i] - segment.embeddings[i]) > 1e-6:
            assert (
                False
            ), f"result[i]: {result[i]}, segment.embeddings[i]: {segment.embeddings[i]}"


def _test_update_segment_vector(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test updating a segment vector."""
    vector_store = create_vector_store_dense(context)
    segment = _create_segment(
        context, org, kb, docsource, f"initial content {uuid.uuid4()}"
    )

    # Save initial segment
    vector_store.save_segments(org, kb, user, [segment])
    initial_vector = vector_store.get_segment_vector(org, kb, segment.segment_uuid)

    # Update segment content
    segment.content = f"Updated content {uuid.uuid4()}"
    vector_store.update_segment_vector(org, kb, user, segment)

    # Get updated vector
    updated_vector = vector_store.get_segment_vector(org, kb, segment.segment_uuid)

    # Verify vectors are different after update
    assert len(initial_vector) == len(updated_vector)
    vectors_are_different = False
    for i in range(len(initial_vector)):
        if abs(initial_vector[i] - updated_vector[i]) > 1e-6:
            vectors_are_different = True
            break
    assert vectors_are_different


def _test_delete_segment_vector(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test deleting a segment vector."""
    vector_store = create_vector_store_dense(context)
    segment = _create_segment(
        context, org, kb, docsource, f"test content {uuid.uuid4()}"
    )

    vector_store.save_segments(org, kb, user, [segment])

    # Delete the segment vector
    assert vector_store.delete_segment_vector(org, kb, segment.segment_uuid) is True

    # Verify that the segment vector no longer exists
    result = vector_store.get_segment_vector(org, kb, segment.segment_uuid)
    assert result == []


def _test_search_in_kb(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test searching for segments in the knowledge base."""
    vector_store = create_vector_store_dense(context)
    test_content = f"test content {uuid.uuid4()}"
    segment = _create_segment(context, org, kb, docsource, test_content)

    vector_store.save_segments(org, kb, user, [segment])

    # Search parameters
    query = test_content
    top_k = 5
    results = vector_store.search_in_kb(org, kb, user, query, top_k)

    # Verify that the search returns results
    assert len(results) > 0
    # check if the first result is the segment we created
    assert results[0].segment_uuid == segment.segment_uuid

    filter = BaseCondition(
        field=Segment.FIELD_DOCUMENT_UUID,
        operator="==",
        value=f"{segment.document_uuid}",
    )
    results = vector_store.search_in_kb(org, kb, user, query, top_k, filter=filter)
    assert len(results) > 0
    assert results[0].segment_uuid == segment.segment_uuid

    # test full text search
    vector_store._rebuild_full_text_index(org, kb, user)
    results = vector_store._full_text_search_in_kb(org, kb, user, query, top_k)
    assert len(results) > 0
    assert results[0].segment_uuid == segment.segment_uuid


def _test_get_segment_vector_not_found(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test getting a non-existent segment vector."""
    vector_store = create_vector_store_dense(context)
    segment = _create_segment(
        context, org, kb, docsource, f"test content {uuid.uuid4()}"
    )

    vector_store.save_segments(org, kb, user, [segment])

    # Test getting a segment vector that does not exist
    result = vector_store.get_segment_vector(org, kb, "non_existent_uuid")
    assert result == []


def _test_delete_segment_vector_not_found(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test deleting a segment vector that does not exist."""
    vector_store = create_vector_store_dense(context)
    segment = _create_segment(
        context, org, kb, docsource, f"test content {uuid.uuid4()}"
    )

    vector_store.save_segments(org, kb, user, [segment])

    # Test deleting a segment vector that does not exist
    result = vector_store.delete_segment_vector(org, kb, "non_existent_uuid")
    assert result is True  # Should return True even if it doesn't exist


def _test_delete_segment_vectors_by_docsink_uuid(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test deleting segment vectors by docsink UUID."""
    vector_store = create_vector_store_dense(context)
    segment = _create_segment(
        context, org, kb, docsource, f"test content {uuid.uuid4()}"
    )

    vector_store.save_segments(org, kb, user, [segment])

    # Call the delete method
    result = vector_store.delete_segment_vectors_by_docsink_uuid(
        org, kb, segment.docsink_uuid
    )

    # Verify that the segment vector was deleted
    assert result is True
    assert vector_store.get_segment_vector(org, kb, segment.segment_uuid) == []


def _test_delete_segment_vectors_by_docsource_uuid(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test deleting segment vectors by docsource UUID."""
    vector_store = create_vector_store_dense(context)
    segment = _create_segment(
        context, org, kb, docsource, f"test content {uuid.uuid4()}"
    )
    vector_store.save_segments(org, kb, user, [segment])

    # Call the delete method
    result = vector_store.delete_segment_vectors_by_docsource_uuid(
        org, kb, docsource.docsource_uuid
    )

    # Verify that the segment vector was deleted
    assert result is True
    assert vector_store.get_segment_vector(org, kb, segment.segment_uuid) == []


def _test_delete_segment_vectors_by_document_id(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test deleting segment vectors by document ID."""
    vector_store = create_vector_store_dense(context)
    segment = _create_segment(
        context, org, kb, docsource, f"test content {uuid.uuid4()}"
    )

    vector_store.save_segments(org, kb, user, [segment])

    # Call the delete method
    result = vector_store.delete_segment_vectors_by_document_id(
        org, kb, segment.document_uuid
    )

    # Verify that the segment vector was deleted
    assert result is True
    assert vector_store.get_segment_vector(org, kb, segment.segment_uuid) == []


def _test_get_segment_vector(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
):
    """Test getting a segment vector."""
    vector_store = create_vector_store_dense(context)
    segment = _create_segment(
        context, org, kb, docsource, f"test content {uuid.uuid4()}"
    )

    vector_store.save_segments(org, kb, user, [segment])

    # Get the segment vector
    result = vector_store.get_segment_vector(org, kb, segment.segment_uuid)

    # Verify the vector matches the segment's embeddings
    assert result is not None
    assert len(result) > 0
    for i in range(len(result)):
        if abs(result[i] - segment.embeddings[i]) > 1e-6:
            assert (
                False
            ), f"result[i]: {result[i]}, segment.embeddings[i]: {segment.embeddings[i]}"
