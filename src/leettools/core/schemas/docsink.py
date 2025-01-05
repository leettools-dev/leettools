from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.core.consts.docsink_status import DocSinkStatus
from leettools.core.schemas.docsource import DocSource

"""
See [README](./README.md) about the usage of different pydantic models.
"""


class DocSinkBase(BaseModel):

    original_doc_uri: str = Field(..., description="The original URI of the document.")
    raw_doc_uri: str = Field(
        ..., description="The URI of the raw document (the docsink)."
    )
    raw_doc_hash: Optional[str] = Field(
        None, description="The hash value of the raw doc."
    )
    size: Optional[int] = Field(None, description="The size of the raw document.")


class DocSinkCreate(DocSinkBase):
    docsource: DocSource = Field(..., description="The docsource object.")


class DocSinkInDBBase(DocSinkBase):
    docsink_uuid: str = Field(..., description="The UUID of the docsink.")

    # information copied from the DocSource
    org_id: str = Field(..., description="The organization ID of the document.")
    kb_id: str = Field(..., description="The knowledge base ID of the document source.")
    docsource_uuids: List[str] = Field(..., description="The UUID of the docsources.")

    # DocSink status
    is_deleted: Optional[bool] = Field(False, description="The deletion flag.")
    docsink_status: Optional[DocSinkStatus] = Field(
        None, description="The status of the docsink."
    )
    expired_at: Optional[datetime] = Field(None, description="The expiration time.")


class DocSinkUpdate(DocSinkInDBBase):
    # in theory the fields in DocSinkCreate should be immutable after creation
    pass


class DocSinkInDB(DocSinkInDBBase):
    created_at: Optional[datetime] = Field(None, description="The creation time.")
    updated_at: Optional[datetime] = Field(None, description="The last update time.")

    @classmethod
    def from_docsink_create(cls, docsink_create: DocSinkCreate) -> "DocSinkInDB":
        ct = time_utils.current_datetime()
        docsource = docsink_create.docsource
        docsink_in_store = cls(
            docsink_uuid="",
            docsource_uuids=[docsource.docsource_uuid],
            org_id=docsource.org_id,
            kb_id=docsource.kb_id,
            original_doc_uri=docsink_create.original_doc_uri,
            raw_doc_uri=docsink_create.raw_doc_uri,
            expired_at=None,
            docsink_status=DocSinkStatus.CREATED,
            created_at=ct,
            updated_at=ct,
        )
        assign_properties(docsink_create, docsink_in_store)
        return docsink_in_store

    @classmethod
    def from_docsink_update(cls, docsink_update: DocSinkUpdate) -> "DocSinkInDB":
        docsink_in_store = cls(
            raw_doc_uri=docsink_update.raw_doc_uri,
            docsink_uuid=docsink_update.docsink_uuid,
            docsource_uuids=docsink_update.docsource_uuids,
            org_id=docsink_update.org_id,
            kb_id=docsink_update.kb_id,
            original_doc_uri=docsink_update.original_doc_uri,
            is_deleted=docsink_update.is_deleted,
            docsink_status=docsink_update.docsink_status,
            updated_at=time_utils.current_datetime(),
        )
        assign_properties(docsink_update, docsink_in_store)
        return docsink_in_store


@add_fieldname_constants
class DocSink(DocSinkInDB):
    """
    This class is used to represent a document sink (docsink) in the system. When
    a DocSource is specified, the pipeline will ingest the document from the source
    according to the specification and store the document in its original form in
    the file system as a docsink.
    """

    @classmethod
    def from_docsink_in_db(cls, docsink_in_db: DocSinkInDB) -> "DocSink":
        docsink = cls(
            docsink_uuid=docsink_in_db.docsink_uuid,
            docsource_uuids=docsink_in_db.docsource_uuids,
            org_id=docsink_in_db.org_id,
            kb_id=docsink_in_db.kb_id,
            original_doc_uri=docsink_in_db.original_doc_uri,
            raw_doc_uri=docsink_in_db.raw_doc_uri,
            is_deleted=docsink_in_db.is_deleted,
            docsink_status=docsink_in_db.docsink_status,
            created_at=docsink_in_db.created_at,
            updated_at=docsink_in_db.updated_at,
            expired_at=docsink_in_db.expired_at,
        )
        assign_properties(docsink_in_db, docsink)
        return docsink


@dataclass
class BaseDocsinkSchema(ABC):
    """Abstract base schema for docsink implementations."""

    TABLE_NAME: str = "TABLE_NAME"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        """Get base column definitions shared across implementations."""
        return {
            DocSink.FIELD_DOCSINK_UUID: "VARCHAR PRIMARY KEY",
            DocSink.FIELD_DOCSOURCE_UUIDS: "VARCHAR",
            DocSink.FIELD_ORG_ID: "VARCHAR",
            DocSink.FIELD_KB_ID: "VARCHAR",
            DocSink.FIELD_ORIGINAL_DOC_URI: "VARCHAR",
            DocSink.FIELD_RAW_DOC_URI: "VARCHAR",
            DocSink.FIELD_IS_DELETED: "BOOLEAN DEFAULT FALSE",
            DocSink.FIELD_RAW_DOC_HASH: "VARCHAR",
            DocSink.FIELD_SIZE: "INTEGER",
            DocSink.FIELD_DOCSINK_STATUS: "VARCHAR",
            DocSink.FIELD_CREATED_AT: "TIMESTAMP",
            DocSink.FIELD_UPDATED_AT: "TIMESTAMP",
            DocSink.FIELD_EXPIRED_AT: "TIMESTAMP",
        }
