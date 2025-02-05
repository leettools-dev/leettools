import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, Field

from leettools.common import exceptions
from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.core.config.performance_configurable import PerfBaseModel
from leettools.core.consts.segment_embedder_type import SegmentEmbedderType

"""
See [README](./README.md) about the usage of different pydantic models.
"""


class KBPerfConfig(PerfBaseModel):
    """
    The configuration for KB that may change its performance in retrieval.
    """

    embedder_type: Optional[str] = Field(
        None,
        description="The type of embedder to use for the KB",
    )
    dense_embedder: Optional[str] = Field(
        None, description="The dense embedder to use for the KB"
    )
    dense_embedder_params: Optional[Dict[str, Any]] = Field(
        None,
        description="The parameters for the dense embedder to use for the KB",
    )
    sparse_embedder: Optional[str] = Field(
        None,
        description="The sparse embedder to use for the KB",
    )
    sparse_embedder_params: Optional[Dict[str, Any]] = Field(
        None,
        description="The parameters for the sparse embedder to use for the KB",
    )
    enable_contextual_retrieval: Optional[bool] = Field(
        False,
        description="Whether to enable contextual retrieval for the KB",
    )


class KBBase(BaseModel):
    name: str = Field(
        ...,
        description="The name of the KB, unique in the same organization",
    )
    description: Optional[str] = Field(None, description="The description of the KB.")
    share_to_public: Optional[bool] = Field(
        False, description="Whether to share the KB to public"
    )
    promotion_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="The promotion metadata, passed to frontend to used in the KB list view",
    )
    owner_id: Optional[str] = Field(
        None,
        description="The owner id of the KB, if None, the user_uuid is the owner",
    )
    is_deleted: Optional[bool] = Field(False, description="Whether the KB is deleted")


class KBCreate(KBBase, KBPerfConfig):
    # these fields can be specified at the creation time
    # they can't be change in the update
    user_uuid: Optional[str] = Field(None, description="The creator uuid of the KB")
    auto_schedule: Optional[bool] = Field(
        True,
        description=(
            "Whether to add the KB to the scheduler. Adhoc KBs should set this to False",
        ),
    )


class KBInDBBase(KBCreate):
    kb_id: Optional[str] = None


@add_fieldname_constants
class KBUpdate(KBBase):

    # we use kb_name as the key to update the kb
    # so we need a new name to update the kb name
    # set to non-null value if we want to rename the kb
    new_name: Optional[str] = Field(
        None,
        description="The new name of the KB, if set, the name of the KB will be updated",
    )

    @classmethod
    def from_kb_in_db_base(KBUpdate, kb_in_db_base: KBInDBBase) -> "KBUpdate":
        # need to copy the non-null fields from kb_in_db_base
        kb_update = KBUpdate(
            name=kb_in_db_base.name,
            share_to_public=kb_in_db_base.share_to_public,
            is_deleted=kb_in_db_base.is_deleted,
        )
        assign_properties(kb_in_db_base, kb_update)
        return kb_update


class KBInDB(KBInDBBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_kb_create(KBInDB, kb_create: KBCreate) -> "KBInDB":
        ct = time_utils.current_datetime()
        if kb_create.user_uuid is not None:
            if kb_create.owner_id is None:
                kb_create.owner_id = kb_create.user_uuid

        kb = KBInDB(
            name=kb_create.name,
            description=kb_create.description,
            embedder_type=kb_create.embedder_type,
            kb_id=str(uuid.uuid4()),
            created_at=ct,
            updated_at=ct,
            owner_id=kb_create.owner_id,
            user_uuid=kb_create.user_uuid,
            auto_schedule=kb_create.auto_schedule,
            enable_contextual_retrieval=kb_create.enable_contextual_retrieval,
        )
        assign_properties(kb_create, kb)
        return kb


@add_fieldname_constants
class KnowledgeBase(KBInDB):
    """
    This class represents a knowledge base entry used by the client
    """

    """
    Extra properties instantiated and returned to client
    """
    owner: Optional[str] = None
    user: Optional[str] = None

    TEST_KB_PREFIX: ClassVar[str] = "test_kb"
    DEFAULT_DESCRIPTION_PREFIX: ClassVar[str] = (
        "Knowledge discovery, curation, and sharing."
    )

    def get_content_instruction(self) -> Optional[str]:
        """
        Get the description as the content instruction if it is not the default.

        We may separate the content instruction from the description in the future.
        """
        if self.description is None:
            return None

        if self.description.startswith(self.DEFAULT_DESCRIPTION_PREFIX):
            return None

        return self.description

    def is_owner(self, user_uuid: str) -> bool:
        # TODO: right now the kb.owner_id is not used, so use kb.user_uuid which
        # is the creator of the kb. When we implement the change owner function
        # we should change the logic here.
        if self.owner_id is not None:
            return self.owner_id == user_uuid
        return self.user_uuid == user_uuid

    def get_owner_name(self) -> str:
        if self.owner is not None:
            return self.owner
        if self.user is not None:
            return self.user
        raise exceptions.UnexpectedCaseException(
            "Both owner and user of the KB are None, this should not happen"
        )

    def get_collection_name(self) -> str:
        return f"{self.kb_id}_kb"

    def extracted_db_prefix(self) -> str:
        return f"{self.kb_id}_extracted_"

    def collection_name_for_extracted_data(self, target_model_name: str) -> str:
        return f"{self.extracted_db_prefix()}{target_model_name}"

    def collection_name_for_extraction_list(self) -> str:
        return f"{self.kb_id}_extraction_list"

    def collection_name_for_metadata(self, metadata_name: str) -> str:
        return f"{self.kb_id}_metadata_{metadata_name}"

    def collection_name_for_table(self, table_name: str) -> str:
        return f"{self.kb_id}_table_{table_name}"

    @classmethod
    def from_kb_in_db(KnowledgeBase, kb_in_db: KBInDB) -> "KnowledgeBase":
        kb = KnowledgeBase(
            name=kb_in_db.name,
            description=kb_in_db.description,
            embedder_type=kb_in_db.embedder_type,
            kb_id=kb_in_db.kb_id,
            created_at=kb_in_db.created_at,
            updated_at=kb_in_db.updated_at,
            owner_id=kb_in_db.owner_id,
            user_uuid=kb_in_db.user_uuid,
            share_to_public=kb_in_db.share_to_public,
            is_deleted=kb_in_db.is_deleted,
            auto_schedule=kb_in_db.auto_schedule,
            enable_contextual_retrieval=kb_in_db.enable_contextual_retrieval,
        )
        assign_properties(kb_in_db, kb)
        return kb


@dataclass
class BaseKBSchema(ABC):
    TABLE_NAME: str = "kb"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        return {
            KnowledgeBase.FIELD_KB_ID: "VARCHAR PRIMARY KEY",
            KnowledgeBase.FIELD_NAME: "VARCHAR",
            KnowledgeBase.FIELD_DESCRIPTION: "VARCHAR",
            KnowledgeBase.FIELD_EMBEDDER_TYPE: "VARCHAR",
            KnowledgeBase.FIELD_DENSE_EMBEDDER: "VARCHAR",
            KnowledgeBase.FIELD_DENSE_EMBEDDER_PARAMS: "VARCHAR",
            KnowledgeBase.FIELD_SPARSE_EMBEDDER: "VARCHAR",
            KnowledgeBase.FIELD_SPARSE_EMBEDDER_PARAMS: "VARCHAR",
            KnowledgeBase.FIELD_USER_UUID: "VARCHAR",
            KnowledgeBase.FIELD_SHARE_TO_PUBLIC: "BOOLEAN",
            KnowledgeBase.FIELD_PROMOTION_METADATA: "VARCHAR",
            KnowledgeBase.FIELD_ENABLE_CONTEXTUAL_RETRIEVAL: "BOOLEAN",
            KnowledgeBase.FIELD_AUTO_SCHEDULE: "BOOLEAN",
            KnowledgeBase.FIELD_CREATED_AT: "TIMESTAMP",
            KnowledgeBase.FIELD_UPDATED_AT: "TIMESTAMP",
            KnowledgeBase.FIELD_OWNER_ID: "VARCHAR",
            KnowledgeBase.FIELD_IS_DELETED: "BOOLEAN",
            KnowledgeBase.FIELD_OWNER: "VARCHAR",
            KnowledgeBase.FIELD_USER: "VARCHAR",
        }
