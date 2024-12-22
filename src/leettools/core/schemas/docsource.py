from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.schedule_config import ScheduleConfig


class IngestConfig(BaseModel):
    flow_options: Dict[str, Any] = {}
    extra_parameters: Dict[str, Any] = {}


"""
See [README](./README.md) about the usage of different pydantic models.
"""


class DocSourceBase(BaseModel):

    kb_id: str = Field(..., description="Knowledge base ID")
    source_type: DocSourceType = Field(..., description="Type of document source")
    uri: str = Field(..., description="The original URI of the document source")
    display_name: Optional[str] = Field(
        None, description="Display name of the document source"
    )
    ingest_config: Optional[IngestConfig] = Field(
        None, description="Ingestion configuration."
    )
    schedule_config: Optional[ScheduleConfig] = Field(
        None, description="Schedule configuration."
    )
    tags: Optional[List[str]] = Field(
        None, description="Tags associated with the document source, used to filter"
    )


class DocSourceCreate(DocSourceBase):
    pass


class DocSourceInDBBase(DocSourceBase):
    # The UUID of the document source after it has been stored
    docsource_uuid: str = Field(..., description="UUID of the document source")
    is_deleted: Optional[bool] = Field(False, description="Deletion flag")
    source_status: Optional[DocSourceStatus] = Field(
        None, description="Status of the document source"
    )


class DocSourceUpdate(DocSourceInDBBase):
    pass


class DocSourceInDB(DocSourceInDBBase):
    created_at: Optional[datetime] = Field(None, description="Creation datetime")
    updated_at: Optional[datetime] = Field(None, description="Last update datetime")

    @classmethod
    def from_docsource_create(
        DocSourceInDB, docsource_create: DocSourceCreate
    ) -> "DocSourceInDB":
        ct = datetime.now()

        docsource_in_store = DocSourceInDB(
            # caller needs to update uuid later document is
            # stored in store and get the uuid back.
            docsource_uuid="",
            kb_id=docsource_create.kb_id,
            source_type=docsource_create.source_type,
            source_status=DocSourceStatus.CREATED,
            uri=docsource_create.uri,
            created_at=ct,
            updated_at=ct,
            ingest_config=docsource_create.ingest_config,
            schedule_config=docsource_create.schedule_config,
            tags=docsource_create.tags,
        )

        assign_properties(docsource_create, docsource_in_store)
        return docsource_in_store

    @classmethod
    def from_docsource_update(
        DocSourceInDB, docsource_update: DocSourceUpdate
    ) -> "DocSourceInDB":
        docsource_in_store = DocSourceInDB(
            docsource_uuid=docsource_update.docsource_uuid,
            source_type=docsource_update.source_type,
            uri=docsource_update.uri,
            kb_id=docsource_update.kb_id,
            is_deleted=docsource_update.is_deleted,
            source_status=docsource_update.source_status,
            updated_at=datetime.now(),
        )
        assign_properties(docsource_update, docsource_in_store)
        return docsource_in_store


@add_fieldname_constants
class DocSource(DocSourceInDB):
    """
    DocSource specifies the source to be ingested and the configuration of the ingestion
    process.
    """

    @classmethod
    def from_docsource_in_db(
        DocSource, docsource_instore: DocSourceInDB
    ) -> "DocSource":
        docsource = DocSource(
            docsource_uuid=docsource_instore.docsource_uuid,
            kb_id=docsource_instore.kb_id,
            source_type=docsource_instore.source_type,
            is_deleted=docsource_instore.is_deleted,
            source_status=docsource_instore.source_status,
            uri=docsource_instore.uri,
            ingest_config=docsource_instore.ingest_config,
            schedule_config=docsource_instore.schedule_config,
            tags=docsource_instore.tags,
        )
        assign_properties(docsource_instore, docsource)
        return docsource

    def is_finished(self) -> bool:
        return self.source_status in [
            DocSourceStatus.COMPLETED,
            DocSourceStatus.FAILED,
            DocSourceStatus.ABORTED,
            DocSourceStatus.PARTIAL,
        ]


@dataclass
class BaseDocSourceSchema(ABC):
    """Abstract base schema for docsource implementations."""

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
            DocSource.FIELD_DOCSOURCE_UUID: "VARCHAR PRIMARY KEY",
            DocSource.FIELD_KB_ID: "VARCHAR",
            DocSource.FIELD_SOURCE_TYPE: "VARCHAR",
            DocSource.FIELD_SOURCE_STATUS: "VARCHAR",
            DocSource.FIELD_URI: "VARCHAR",
            DocSource.FIELD_IS_DELETED: "BOOLEAN DEFAULT FALSE",
            DocSource.FIELD_DISPLAY_NAME: "VARCHAR",
            DocSource.FIELD_INGEST_CONFIG: "JSON",
            DocSource.FIELD_SCHEDULE_CONFIG: "JSON",
            DocSource.FIELD_TAGS: "JSON",
            DocSource.FIELD_CREATED_AT: "TIMESTAMP",
            DocSource.FIELD_UPDATED_AT: "TIMESTAMP",
        }
