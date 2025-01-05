from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.core.consts.document_status import DocumentStatus
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.document_metadata import DocumentSummary

"""
See [README](./README.md) about the usage of different pydantic models.
"""


class DocumentBase(BaseModel):
    """
    Converted markdown documents.
    """

    content: str = Field(..., description="The content of the document")
    doc_uri: str = Field(..., description="The URI of the document")


# Properties to receive on document creation
class DocumentCreate(DocumentBase):
    docsink: DocSink = Field(..., description="The docsink object")


# Properties to receive on document update
class DocumentInDBBase(DocumentBase):
    document_uuid: str = Field(..., description="The UUID of the document")

    # these are the essential fields copied from the DocSink object
    org_id: str = Field(..., description="The organization ID of the document")
    kb_id: str = Field(..., description="The UUID of the knowledge base")
    docsink_uuid: str = Field(..., description="The UUID of the docsink")
    original_uri: Optional[str] = Field(
        None, description="The original URI of the document"
    )
    docsource_uuids: List[str] = Field(..., description="The UUID of the docsources")
    expired_at: Optional[datetime] = Field(None, description="Expiration timestamp.")

    # status of the document
    split_status: Optional[DocumentStatus] = Field(
        None, description="If the document has been split"
    )
    embed_status: Optional[DocumentStatus] = Field(
        None, description="If the document has been embedded"
    )
    is_deleted: Optional[bool] = Field(False, description="If the document is deleted")

    # metdata for the document
    auto_summary: Optional[DocumentSummary] = Field(
        None,
        description=(
            "Auto-generated summary of the document, will be used if no manual summary "
            "is provided.",
        ),
    )
    manual_summary: Optional[DocumentSummary] = Field(
        None,
        description=(
            "Manually edited summary of the document, will take precedence over the "
            "auto-generated summary directly stored in the document.",
        ),
    )


# Properties to receive on document update
class DocumentUpdate(DocumentInDBBase):
    pass


# Properties shared by models stored in DB
class DocumentInDB(DocumentInDBBase):
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    @classmethod
    def from_document_create(
        DocumentInDB, document_create: DocumentCreate
    ) -> "DocumentInDB":
        ct = time_utils.current_datetime()
        docsink = document_create.docsink
        document_in_store = DocumentInDB(
            # caller needs to update uuid later document is
            # stored in store and get the uuid back.
            document_uuid="",
            content=document_create.content,
            doc_uri=document_create.doc_uri,
            org_id=docsink.org_id,
            kb_id=docsink.kb_id,
            docsink_uuid=docsink.docsink_uuid,
            original_uri=docsink.original_doc_uri,
            docsource_uuids=docsink.docsource_uuids,
            expired_at=docsink.expired_at,
            split_status=DocumentStatus.CREATED,
            embed_status=DocumentStatus.CREATED,
            created_at=ct,
            updated_at=ct,
        )
        return document_in_store


@add_fieldname_constants
class Document(DocumentInDB):
    """
    Converted and cleaned-up markdown documents.
    """

    @classmethod
    def from_document_in_db(Document, document_in_store: DocumentInDB) -> "Document":
        document = Document(
            document_uuid=document_in_store.document_uuid,
            content=document_in_store.content,
            docsink_uuid=document_in_store.docsink_uuid,
            docsource_uuids=document_in_store.docsource_uuids,
            org_id=document_in_store.org_id,
            kb_id=document_in_store.kb_id,
            doc_uri=document_in_store.doc_uri,
            is_deleted=document_in_store.is_deleted,
        )
        assign_properties(document_in_store, document)
        return document

    def summary(self) -> DocumentSummary:
        # return any field in the manual summary if it is set
        if self.manual_summary is None:
            return self.auto_summary

        return DocumentSummary(
            summary=(
                self.manual_summary.summary
                if self.manual_summary
                else self.auto_summary.summary
            ),
            keywords=(
                self.manual_summary.keywords
                if self.manual_summary
                else self.auto_summary.keywords
            ),
            links=(
                self.manual_summary.links
                if self.manual_summary
                else self.auto_summary.links
            ),
            authors=(
                self.manual_summary.authors
                if self.manual_summary
                else self.auto_summary.authors
            ),
            content_date=(
                self.manual_summary.content_date
                if self.manual_summary
                else self.auto_summary.content_date
            ),
            relevance_score=(
                self.manual_summary.relevance_score
                if self.manual_summary
                else self.auto_summary.relevance_score
            ),
        )


@dataclass
class BaseDocumentSchema(ABC):
    """Abstract base schema for document implementations."""

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
            Document.FIELD_DOCUMENT_UUID: "VARCHAR PRIMARY KEY",
            Document.FIELD_DOCSINK_UUID: "VARCHAR",
            Document.FIELD_DOCSOURCE_UUIDS: "VARCHAR",
            Document.FIELD_ORG_ID: "VARCHAR",
            Document.FIELD_KB_ID: "VARCHAR",
            Document.FIELD_DOC_URI: "VARCHAR",
            Document.FIELD_CONTENT: "TEXT",
            Document.FIELD_ORIGINAL_URI: "VARCHAR",
            Document.FIELD_SPLIT_STATUS: "VARCHAR",
            Document.FIELD_EMBED_STATUS: "VARCHAR",
            Document.FIELD_IS_DELETED: "BOOLEAN DEFAULT FALSE",
            Document.FIELD_AUTO_SUMMARY: "JSON",
            Document.FIELD_MANUAL_SUMMARY: "JSON",
            Document.FIELD_CREATED_AT: "TIMESTAMP",
            Document.FIELD_UPDATED_AT: "TIMESTAMP",
            Document.FIELD_EXPIRED_AT: "TIMESTAMP",
        }
