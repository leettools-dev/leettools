import os
import uuid
from pathlib import Path

import pytest

from leettools.common.logging import EventLogger
from leettools.context_manager import ContextManager
from leettools.core.consts.docsink_status import DocSinkStatus
from leettools.core.repo._impl.duckdb.docsink_store_duckdb import DocsinkStoreDuckDB
from leettools.core.schemas.docsink import DocSink, DocSinkCreate, DocSinkUpdate
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.settings import SystemSettings


@pytest.fixture()
def test_kb_identifier() -> str:
    return f"test_kbid_{str(uuid.uuid4())}"


@pytest.fixture(autouse=True)
def settings():
    """Create test settings with temporary DB path."""
    test_db_path = Path("tests/data/test_db")
    test_db_path.mkdir(parents=True, exist_ok=True)

    context = ContextManager().get_context()
    context.reset(is_test=True)

    settings = context.settings
    settings.DOC_STORE_TYPE = "duckdb"
    settings.DUCKDB_PATH = str(test_db_path)
    settings.DUCKDB_FILE = str(uuid.uuid4()) + ".db"
    return settings


@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests."""
    EventLogger.set_global_default_level("DEBUG")


@pytest.fixture(autouse=True)
def cleanup(settings):
    """Clean up test database after tests."""
    yield
    db_path = Path(settings.DUCKDB_PATH) / settings.DUCKDB_FILE
    if db_path.exists():
        os.remove(db_path)


@pytest.fixture
def store(settings: SystemSettings):
    """Create test DocsinkStoreDuckDB instance."""
    return DocsinkStoreDuckDB(settings, is_test=True)


@pytest.fixture
def org():
    """Create test organization."""
    return Org(org_id="test_org_id", name="test_org", description="Test Org")


@pytest.fixture
def kb(test_kb_identifier: str):
    """Create test knowledge base."""
    return KnowledgeBase(name="test_kb", kb_id=test_kb_identifier)


@pytest.fixture
def docsource(test_kb_identifier: str):
    """Create test document source."""
    return DocSource(
        docsource_uuid=str(uuid.uuid4()),
        kb_id=test_kb_identifier,
        source_type="file",
        uri="test_uri",
        source_location="test_location",
    )


@pytest.fixture
def docsink_create(kb: KnowledgeBase, docsource: DocSource):
    """Create a test DocSinkCreate instance."""
    return DocSinkCreate(
        docsource_uuid=docsource.docsource_uuid,
        kb_id=kb.kb_id,
        original_doc_uri="test_uri",
        raw_doc_uri="test_raw_uri",
        raw_doc_hash="test_hash",
    )


def test_create_docsink(
    store: DocsinkStoreDuckDB,
    org: Org,
    kb: KnowledgeBase,
    docsink_create: DocSinkCreate,
):
    """Test creating a new docsink."""
    docsink = store.create_docsink(org, kb, docsink_create)

    assert isinstance(docsink, DocSink)
    assert docsink.docsource_uuid == docsink_create.docsource_uuid
    assert docsink.kb_id == kb.kb_id
    assert docsink.original_doc_uri == "test_uri"
    assert docsink.raw_doc_uri == "test_raw_uri"
    assert docsink.raw_doc_hash == "test_hash"
    assert docsink.docsink_status == DocSinkStatus.CREATED


def test_create_docsink_with_same_hash(
    store: DocsinkStoreDuckDB,
    org: Org,
    kb: KnowledgeBase,
    docsink_create: DocSinkCreate,
):
    """Test creating a docsink with duplicate hash."""
    first_docsink = store.create_docsink(org, kb, docsink_create)

    # Create second docsink with same hash but different URI
    second_create = DocSinkCreate(
        docsource_uuid=docsink_create.docsource_uuid,
        kb_id=kb.kb_id,
        original_doc_uri="test_uri",
        raw_doc_uri="test_raw_uri",
        raw_doc_hash=docsink_create.raw_doc_hash,
    )

    second_docsink = store.create_docsink(org, kb, second_create)
    assert second_docsink.docsink_uuid == first_docsink.docsink_uuid
    assert "test_uri" in second_docsink.extra_original_doc_uri


def test_create_duplicate_docsink(
    store: DocsinkStoreDuckDB,
    org: Org,
    kb: KnowledgeBase,
    docsink_create: DocSinkCreate,
):
    """Test creating a docsink with duplicate hash."""
    first_docsink = store.create_docsink(org, kb, docsink_create)

    # Create second docsink with same hash but different URI
    second_create = DocSinkCreate(
        docsource_uuid=docsink_create.docsource_uuid,
        kb_id=kb.kb_id,
        original_doc_uri="different_uri",
        raw_doc_uri="different_raw_uri",
        raw_doc_hash=docsink_create.raw_doc_hash,
    )

    second_docsink = store.create_docsink(org, kb, second_create)
    assert second_docsink.docsink_uuid == first_docsink.docsink_uuid
    assert "different_uri" in second_docsink.extra_original_doc_uri


def test_get_docsink_by_id(
    store: DocsinkStoreDuckDB,
    org: Org,
    kb: KnowledgeBase,
    docsink_create: DocSinkCreate,
):
    """Test retrieving a docsink by ID."""
    created_docsink = store.create_docsink(org, kb, docsink_create)
    retrieved_docsink = store.get_docsink_by_id(org, kb, created_docsink.docsink_uuid)

    assert retrieved_docsink is not None
    assert retrieved_docsink.docsink_uuid == created_docsink.docsink_uuid
    assert isinstance(retrieved_docsink, DocSink)

    retrieved_docsink = store.get_docsink_by_id(org, kb, "invalid-uuid")
    assert retrieved_docsink is None


def test_delete_docsink(
    store: DocsinkStoreDuckDB,
    org: Org,
    kb: KnowledgeBase,
    docsink_create: DocSinkCreate,
):
    """Test deleting a docsink."""
    created_docsink = store.create_docsink(org, kb, docsink_create)
    result = store.delete_docsink(org, kb, created_docsink)

    assert result is True
    deleted_docsink = store.get_docsink_by_id(org, kb, created_docsink.docsink_uuid)
    assert deleted_docsink.is_deleted is True


def test_get_docsinks_for_kb(
    store: DocsinkStoreDuckDB,
    org: Org,
    kb: KnowledgeBase,
    docsink_create: DocSinkCreate,
    docsource: DocSource,
):
    """Test retrieving all docsinks for a knowledge base."""
    created_docsinks = []
    for i in range(3):
        docsink_create = DocSinkCreate(
            docsource_uuid=docsource.docsource_uuid,
            kb_id=kb.kb_id,
            original_doc_uri=f"test_uri_{i}",
            raw_doc_uri=f"test_raw_uri_{i}",
            raw_doc_hash=f"test_hash_{i}",
        )
        created_docsinks.append(store.create_docsink(org, kb, docsink_create))

    retrieved_docsinks = store.get_docsinks_for_kb(org, kb)
    assert len(retrieved_docsinks) == 3
    assert all(isinstance(d, DocSink) for d in retrieved_docsinks)


def test_get_docsinks_for_docsource(
    store: DocsinkStoreDuckDB,
    org: Org,
    kb: KnowledgeBase,
    docsink_create: DocSinkCreate,
    docsource: DocSource,
):
    """Test retrieving docsinks for a specific docsource."""
    created_docsink = store.create_docsink(org, kb, docsink_create)
    retrieved_docsinks = store.get_docsinks_for_docsource(org, kb, docsource)

    assert len(retrieved_docsinks) == 1
    assert retrieved_docsinks[0].docsink_uuid == created_docsink.docsink_uuid

    retrieved_docsinks = store.get_docsinks_for_docsource(
        org, kb, docsource, check_extra=True
    )
    assert len(retrieved_docsinks) == 1
    assert retrieved_docsinks[0].docsink_uuid == created_docsink.docsink_uuid


def test_update_docsink(
    store: DocsinkStoreDuckDB,
    org: Org,
    kb: KnowledgeBase,
    docsink_create: DocSinkCreate,
):
    """Test updating a docsink."""
    # First create a docsink
    created_docsink = store.create_docsink(org, kb, docsink_create)
    assert created_docsink is not None

    # Create update with the existing UUID
    update_data = DocSinkUpdate(
        docsink_uuid=created_docsink.docsink_uuid,  # Important: use existing UUID
        docsource_uuid=created_docsink.docsource_uuid,
        kb_id=created_docsink.kb_id,
        original_doc_uri=created_docsink.original_doc_uri,
        raw_doc_uri=created_docsink.raw_doc_uri,
        docsink_status=DocSinkStatus.COMPLETED,
    )

    # Perform update
    updated_docsink = store.update_docsink(org, kb, update_data)

    # Verify update
    assert updated_docsink is not None
    assert updated_docsink.docsink_uuid == created_docsink.docsink_uuid
    assert updated_docsink.docsink_status == DocSinkStatus.COMPLETED


def test_create_duplicate_uri_docsink(
    store: DocsinkStoreDuckDB,
    org: Org,
    kb: KnowledgeBase,
    docsink_create: DocSinkCreate,
):
    """Test creating a docsink with duplicate URIs."""
    # Create first docsink
    first_docsink = store.create_docsink(org, kb, docsink_create)
    assert first_docsink is not None

    # Create second docsink with same URIs but different hash
    second_create = DocSinkCreate(
        docsource_uuid=docsink_create.docsource_uuid,
        kb_id=kb.kb_id,
        original_doc_uri=docsink_create.original_doc_uri,  # Same URI
        raw_doc_uri=docsink_create.raw_doc_uri,  # Same URI
        raw_doc_hash="different_hash",  # Different hash
    )

    # Should return the existing docsink
    second_docsink = store.create_docsink(org, kb, second_create)
    assert second_docsink is not None
    assert second_docsink.docsink_uuid == first_docsink.docsink_uuid
    assert (
        second_docsink.raw_doc_hash == first_docsink.raw_doc_hash
    )  # Should keep original hash
    assert second_docsink.original_doc_uri == first_docsink.original_doc_uri
    assert second_docsink.raw_doc_uri == first_docsink.raw_doc_uri
