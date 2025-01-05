import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import ChatAnswerItem


class CHBase(BaseModel):
    name: str = Field(
        ...,
        description=(
            "The name of the chat history, if not set, the first x characters of the "
            "first query in the chat will be used"
        ),
    )
    org_id: str = Field(..., description="The organization ID.")
    kb_id: str = Field(..., description="The knowledge base ID")
    creator_id: str = Field(..., description="The user ID of the creator.")
    article_type: str = Field(
        ArticleType.CHAT.value, description="The article type used in the chat"
    )
    description: Optional[str] = Field(
        None,
        description="The description of the chat that will be displayed in the chat list.",
    )
    share_to_public: Optional[bool] = Field(
        False, description="Whether the chat is shared to the public."
    )


class CHCreate(CHBase):
    pass


class CHInDBBase(CHBase):
    chat_id: str = Field(
        None,
        description="The unique chat ID. If not set, it will be generated automatically.",
    )
    owner_id: Optional[str] = Field(
        None,
        description="The user ID of the owner. If not set, it will be the same as the creator.",
    )


# TODO: we should only update the name, description, and share_to_public
class CHUpdate(CHInDBBase):
    pass


@add_fieldname_constants
class CHMetadata(BaseModel):
    """
    This metadata is computed from data in the DB and returned to the client for display.
    For shared items such as research articles, the metadata will be computed from the
    data in the DB and returned to client to display.
    """

    flow_type: Optional[str] = Field(
        None, description="The flow type used in the result."
    )
    result_snippet: Optional[str] = Field(
        None, description="The result snippet of the result."
    )
    img_link: Optional[str] = Field(None, description="The image link of the result.")


class CHInDB(CHInDBBase):
    created_at: Optional[datetime] = Field(None, description="The creation timestamp.")
    updated_at: Optional[datetime] = Field(
        None, description="The last update timestamp."
    )
    queries: Optional[list[ChatQueryItem]] = Field(
        None, description="The list of chat query items."
    )
    answers: Optional[list[ChatAnswerItem]] = Field(
        None, description="The list of chat answer items."
    )
    metadata: Optional[CHMetadata] = Field(
        None, description="The chat history metadata."
    )

    @classmethod
    def from_ch_create(CHInDB, ch_create: CHCreate) -> "CHInDB":
        ct = time_utils.current_datetime()
        ch = CHInDB(
            name=ch_create.name,
            org_id=ch_create.org_id,
            kb_id=ch_create.kb_id,
            description=ch_create.description,
            article_type=ch_create.article_type,
            chat_id=str(uuid.uuid4()),
            created_at=ct,
            updated_at=ct,
            creator_id=ch_create.creator_id,
            owner_id=ch_create.creator_id,
            queries=[],
            answers=[],
        )
        assign_properties(ch_create, ch)
        return ch


@add_fieldname_constants
class ChatHistory(CHInDB):
    """
    This class represents a Chat History entry used by the client.

    Note that "ChatHistory" main contails different kinds user query results:
    - chat: a sequence of user queries and system responses
    - digest: a multi-section article to summarize the search results
    - search: a list of top search results that match the query
    and etc.
    """

    #
    kb_name: Optional[str] = Field(
        None, description="For adhoc chat, we need to return the kb_name created."
    )

    @classmethod
    def from_ch_in_db(ChatHistory, ch_in_db: CHInDB) -> "ChatHistory":
        # we need to assignt attributes with non-None values
        # also complext objects that we do not want to deep-copy
        ch = ChatHistory(
            name=ch_in_db.name,
            org_id=ch_in_db.org_id,
            kb_id=ch_in_db.kb_id,
            creator_id=ch_in_db.creator_id,
            article_type=ch_in_db.article_type,
            share_to_public=ch_in_db.share_to_public,
            queryies=ch_in_db.queries,
            answers=ch_in_db.answers,
            metadata=ch_in_db.metadata,
        )
        assign_properties(ch_in_db, ch)
        return ch


@dataclass
class BaseChatHistorySchema(ABC):
    """Abstract base schema for chat history implementations."""

    TABLE_NAME: str = "chat_history"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        """Get base column definitions shared across implementations."""
        return {
            ChatHistory.FIELD_CHAT_ID: "VARCHAR PRIMARY KEY",
            ChatHistory.FIELD_NAME: "VARCHAR",
            ChatHistory.FIELD_KB_ID: "VARCHAR",
            ChatHistory.FIELD_CREATOR_ID: "VARCHAR",
            ChatHistory.FIELD_ARTICLE_TYPE: "VARCHAR",
            ChatHistory.FIELD_DESCRIPTION: "TEXT",
            ChatHistory.FIELD_SHARE_TO_PUBLIC: "BOOLEAN DEFAULT FALSE",
            ChatHistory.FIELD_ORG_ID: "VARCHAR",
            ChatHistory.FIELD_OWNER_ID: "VARCHAR",
            ChatHistory.FIELD_CREATED_AT: "TIMESTAMP",
            ChatHistory.FIELD_UPDATED_AT: "TIMESTAMP",
            ChatHistory.FIELD_QUERIES: "VARCHAR",
            ChatHistory.FIELD_ANSWERS: "VARCHAR",
            ChatHistory.FIELD_METADATA: "VARCHAR",
            ChatHistory.FIELD_KB_NAME: "VARCHAR",
        }
