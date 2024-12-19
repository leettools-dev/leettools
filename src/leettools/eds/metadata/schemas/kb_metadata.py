from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.common.utils.obj_utils import add_fieldname_constants


@add_fieldname_constants
class KBMetadata(BaseModel):
    kb_id: str
    kb_name: str
    created_at: datetime

    # the keys are the docsoure type
    number_of_docsources: Optional[Dict[str, int]] = None
    number_of_docsinks: Optional[Dict[str, int]] = None
    number_of_documents: Optional[Dict[str, int]] = None
    raw_data_size: Optional[Dict[str, int]] = None

    processed_data_size: Optional[Dict[str, int]] = None
    top_keywords: Optional[Dict[str, int]] = None
    top_domains: Optional[Dict[str, int]] = None
    top_links: Optional[Dict[str, int]] = None
    top_authors: Optional[Dict[str, int]] = None


@dataclass
class BaseKBMetadataSchema(ABC):
    """Abstract base schema for KB metadata."""

    TABLE_NAME: str = "kb_metadata"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, Any]:
        return {
            KBMetadata.FIELD_KB_ID: "VARCHAR PRIMARY KEY",
            KBMetadata.FIELD_KB_NAME: "VARCHAR",
            KBMetadata.FIELD_CREATED_AT: "TIMESTAMP",
            KBMetadata.FIELD_NUMBER_OF_DOCSINKS: "VARCHAR",
            KBMetadata.FIELD_NUMBER_OF_DOCSOURCES: "VARCHAR",
            KBMetadata.FIELD_NUMBER_OF_DOCUMENTS: "VARCHAR",
            KBMetadata.FIELD_RAW_DATA_SIZE: "VARCHAR",
            KBMetadata.FIELD_PROCESSED_DATA_SIZE: "VARCHAR",
            KBMetadata.FIELD_TOP_KEYWORDS: "VARCHAR",
            KBMetadata.FIELD_TOP_DOMAINS: "VARCHAR",
            KBMetadata.FIELD_TOP_LINKS: "VARCHAR",
            KBMetadata.FIELD_TOP_AUTHORS: "VARCHAR",
        }
