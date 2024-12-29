import os
import uuid
from pathlib import Path

import pytest

from leettools.common.exceptions import UnexpectedCaseException
from leettools.common.logging import EventLogger
from leettools.context_manager import ContextManager
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.repo._impl.duckdb.docsource_store_duckdb import DocsourceStoreDuckDB
from leettools.core.schemas.docsource import (
    DocSource,
    DocSourceCreate,
    DocSourceUpdate,
    IngestConfig,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.schedule_config import ScheduleConfig


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
def store(settings):
    """Create test DocsourceStoreDuckDB instance."""
    return DocsourceStoreDuckDB(settings, is_test=True)


@pytest.fixture
def org():
    """Create test organization."""
    return Org(org_id="test_org_id", name="test_org", description="Test Org")


@pytest.fixture
def test_kb_identifier() -> str:
    return f"test_kbid_{str(uuid.uuid4())}"


@pytest.fixture
def kb(test_kb_identifier: str):
    """Create test knowledge base."""
    return KnowledgeBase(name="test_kb", kb_id=test_kb_identifier)


@pytest.fixture
def docsource_create(test_kb_identifier: str):
    """Create test DocSourceCreate instance."""
    return DocSourceCreate(
        kb_id=test_kb_identifier,
        source_type=DocSourceType.FILE,
        uri="test_uri",
        display_name="Test Doc",
        ingest_config=IngestConfig(),
        schedule_config=ScheduleConfig(),
        tags=["test"],
    )


def test_create_docsource(store, org, kb, docsource_create):
    """Test creating a new docsource."""
    docsource = store.create_docsource(org, kb, docsource_create)

    assert isinstance(docsource, DocSource)
    assert docsource.kb_id == kb.kb_id
    assert docsource.uri == docsource_create.uri
    assert docsource.source_type == DocSourceType.FILE
    assert docsource.docsource_status == DocSourceStatus.CREATED
    assert docsource.tags == ["test"]


def test_get_docsource(store, org, kb, docsource_create):
    """Test retrieving a docsource."""
    created = store.create_docsource(org, kb, docsource_create)
    retrieved = store.get_docsource(org, kb, created.docsource_uuid)

    assert retrieved is not None
    assert retrieved.docsource_uuid == created.docsource_uuid
    assert isinstance(retrieved, DocSource)

    # Test non-existent docsource
    retrieved = store.get_docsource(org, kb, str(uuid.uuid4()))
    assert retrieved is None


def test_delete_docsource(store, org, kb, docsource_create):
    """Test deleting a docsource."""
    created = store.create_docsource(org, kb, docsource_create)
    result = store.delete_docsource(org, kb, created)

    assert result is True
    retrieved = store.get_docsource(org, kb, created.docsource_uuid)
    assert retrieved.is_deleted is True
    assert retrieved.docsource_status == DocSourceStatus.ABORTED


def test_update_docsource(store, org, kb, docsource_create):
    """Test updating a docsource."""
    created = store.create_docsource(org, kb, docsource_create)

    update_data = DocSourceUpdate(
        docsource_uuid=created.docsource_uuid,
        kb_id=created.kb_id,
        source_type=DocSourceType.FILE,
        uri="test_uri",
        docsource_status=DocSourceStatus.PROCESSING,
        display_name="Updated Name",
    )

    updated = store.update_docsource(org, kb, update_data)
    assert updated is not None
    assert updated.docsource_uuid == created.docsource_uuid
    assert updated.docsource_status == DocSourceStatus.PROCESSING
    assert updated.display_name == "Updated Name"


def test_get_docsources_for_kb(store, org, kb, docsource_create):
    """Test retrieving all docsources for a knowledge base."""
    # Create multiple docsources
    first = store.create_docsource(org, kb, docsource_create)

    second_create = DocSourceCreate(
        kb_id=kb.kb_id,
        source_type=DocSourceType.URL,
        uri="test_uri_2",
        display_name="Test Doc 2",
    )
    second = store.create_docsource(org, kb, second_create)

    results = store.get_docsources_for_kb(org, kb)
    assert len(results) == 2
    assert all(ds.kb_id == kb.kb_id for ds in results)


def test_wait_for_docsource_immediate_completion(store, org, kb, docsource_create):
    """Test waiting for docsource that's already completed."""
    created = store.create_docsource(org, kb, docsource_create)
    update = DocSourceUpdate(
        docsource_uuid=created.docsource_uuid,
        kb_id=created.kb_id,
        source_type=DocSourceType.FILE,
        uri="test_uri",
        docsource_status=DocSourceStatus.COMPLETED,
    )
    store.update_docsource(org, kb, update)

    result = store.wait_for_docsource(org, kb, created, timeout_in_secs=1)
    assert result is True


def test_wait_for_docsource_failure(store, org, kb, docsource_create):
    """Test waiting for docsource that fails processing."""
    created = store.create_docsource(org, kb, docsource_create)

    update = DocSourceUpdate(
        docsource_uuid=created.docsource_uuid,
        kb_id=created.kb_id,
        source_type=DocSourceType.FILE,
        uri="test_uri",
        docsource_status=DocSourceStatus.FAILED,
    )
    store.update_docsource(org, kb, update)

    result = store.wait_for_docsource(org, kb, created, timeout_in_secs=1)
    assert result is True


def test_wait_for_docsource_no_timeout(store, org, kb, docsource_create):
    """Test waiting for docsource with no timeout."""
    created = store.create_docsource(org, kb, docsource_create)

    def delayed_update():
        import time

        time.sleep(0.5)
        update = DocSourceUpdate(
            docsource_uuid=created.docsource_uuid,
            kb_id=created.kb_id,
            source_type=DocSourceType.FILE,
            uri="test_uri",
            docsource_status=DocSourceStatus.COMPLETED,
        )
        store.update_docsource(org, kb, update)

    import threading

    update_thread = threading.Thread(target=delayed_update)
    update_thread.start()

    result = store.wait_for_docsource(org, kb, created, timeout_in_secs=None)
    assert result is True
    update_thread.join()


def test_wait_for_nonexistent_docsource(store, org, kb):
    """Test waiting for a non-existent docsource."""
    non_existent = DocSource(
        docsource_uuid=str(uuid.uuid4()),
        kb_id=kb.kb_id,
        source_type=DocSourceType.FILE,
        uri="test_uri",
    )

    with pytest.raises(UnexpectedCaseException) as exc_info:
        store.wait_for_docsource(org, kb, non_existent, timeout_in_secs=1)
    assert "not found in the DB" in str(exc_info.value)


def test_wait_for_docsource_processing_to_completed(store, org, kb, docsource_create):
    """Test waiting for docsource that transitions from PROCESSING to COMPLETED."""
    created = store.create_docsource(org, kb, docsource_create)

    # Update status to PROCESSING
    processing_update = DocSourceUpdate(
        docsource_uuid=created.docsource_uuid,
        kb_id=created.kb_id,
        source_type=DocSourceType.FILE,
        uri="test_uri",
        docsource_status=DocSourceStatus.PROCESSING,
    )
    store.update_docsource(org, kb, processing_update)

    def delayed_completion():
        import time

        time.sleep(0.5)
        completed_update = DocSourceUpdate(
            docsource_uuid=created.docsource_uuid,
            kb_id=created.kb_id,
            source_type=DocSourceType.FILE,
            uri="test_uri",
            docsource_status=DocSourceStatus.COMPLETED,
        )
        store.update_docsource(org, kb, completed_update)

    import threading

    update_thread = threading.Thread(target=delayed_completion)
    update_thread.start()

    result = store.wait_for_docsource(org, kb, created)
    assert result is True
    update_thread.join()

    processing_update = DocSourceUpdate(
        docsource_uuid=created.docsource_uuid,
        kb_id=created.kb_id,
        source_type=DocSourceType.FILE,
        uri="test_uri",
        docsource_status=DocSourceStatus.PROCESSING,
    )
    store.update_docsource(org, kb, processing_update)
    result = store.wait_for_docsource(org, kb, created, timeout_in_secs=1)
    assert result == False
