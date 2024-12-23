from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.core.consts.document_status import DocumentStatus
from leettools.core.schemas.document_metadata import DocumentSummary

"""
See [README](./README.md) about the usage of different pydantic models.
"""


class DocumentBase(BaseModel):
    """
    Converted markdown documents.
    """

    content: str = Field(..., description="The content of the document")
    docsink_uuid: str = Field(..., description="The UUID of the docsink")
    docsource_uuid: str = Field(..., description="The UUID of the docsource")
    kb_id: str = Field(..., description="The UUID of the knowledge base")
    doc_uri: str = Field(..., description="The URI of the document")
    original_uri: Optional[str] = Field(
        None, description="The original URI of the document"
    )


# Properties to receive on document creation
class DocumentCreate(DocumentBase):
    pass


# Properties to receive on document update
class DocumentInDBBase(DocumentBase):
    document_uuid: str = Field(..., description="The UUID of the document")
    split_status: Optional[DocumentStatus] = Field(
        None, description="If the document has been split"
    )
    embed_status: Optional[DocumentStatus] = Field(
        None, description="If the document has been embedded"
    )
    is_deleted: Optional[bool] = Field(False, description="If the document is deleted")

    # metdata for the document
    # TODO: maybe use DocumentSummary directly here
    summary: Optional[str] = Field(None, description="The summary of the document")
    keywords: Optional[List[str]] = Field(
        None, description="Keywords found in the document"
    )
    content_date: Optional[datetime] = Field(None, description="Date of the document")
    authors: Optional[List[str]] = Field(None, description="Authors of the document")
    links: Optional[List[str]] = Field(None, description="Links found in the document")
    relevance_score: Optional[int] = Field(
        None, description="Relevance score to the topic of the Knowledge Base"
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
    # The date the document was created
    created_at: Optional[datetime] = Field(
        None, description="The date the document was created"
    )
    # The date the document was updated
    updated_at: Optional[datetime] = Field(
        None, description="The date the document was updated"
    )

    @classmethod
    def from_document_create(
        DocumentInDB, document_create: DocumentCreate
    ) -> "DocumentInDB":
        ct = datetime.now()
        document_in_store = DocumentInDB(
            # caller needs to update uuid later document is
            # stored in store and get the uuid back.
            document_uuid="",
            content=document_create.content,
            docsink_uuid=document_create.docsink_uuid,
            docsource_uuid=document_create.docsource_uuid,
            kb_id=document_create.kb_id,
            doc_uri=document_create.doc_uri,
            split_status=DocumentStatus.CREATED,
            embed_status=DocumentStatus.CREATED,
            created_at=ct,
            updated_at=ct,
        )
        assign_properties(document_create, document_in_store)
        return document_in_store

    @classmethod
    def from_document_update(
        DocumentInDB, document_update: DocumentUpdate
    ) -> "DocumentInDB":
        # uuid from the update should be the same as the one in store
        # the caller should ensure that
        document_in_store = DocumentInDB(
            content=document_update.content,
            document_uuid=document_update.document_uuid,
            docsink_uuid=document_update.docsink_uuid,
            docsource_uuid=document_update.docsource_uuid,
            kb_id=document_update.kb_id,
            doc_uri=document_update.doc_uri,
            updated_at=datetime.now(),
            is_deleted=document_update.is_deleted,
        )
        assign_properties(document_update, document_in_store)
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
            docsource_uuid=document_in_store.docsource_uuid,
            kb_id=document_in_store.kb_id,
            doc_uri=document_in_store.doc_uri,
            is_deleted=document_in_store.is_deleted,
        )
        assign_properties(document_in_store, document)
        return document


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
            Document.FIELD_DOCSOURCE_UUID: "VARCHAR",
            Document.FIELD_KB_ID: "VARCHAR",
            Document.FIELD_DOC_URI: "VARCHAR",
            Document.FIELD_CONTENT: "TEXT",
            Document.FIELD_ORIGINAL_URI: "VARCHAR",
            Document.FIELD_SPLIT_STATUS: "VARCHAR",
            Document.FIELD_EMBED_STATUS: "VARCHAR",
            Document.FIELD_IS_DELETED: "BOOLEAN DEFAULT FALSE",
            Document.FIELD_SUMMARY: "TEXT",
            Document.FIELD_KEYWORDS: "JSON",
            Document.FIELD_CONTENT_DATE: "TIMESTAMP",
            Document.FIELD_AUTHORS: "JSON",
            Document.FIELD_LINKS: "JSON",
            Document.FIELD_RELEVANCE_SCORE: "INTEGER",
            Document.FIELD_MANUAL_SUMMARY: "JSON",
            Document.FIELD_CREATED_AT: "TIMESTAMP",
            Document.FIELD_UPDATED_AT: "TIMESTAMP",
        }
