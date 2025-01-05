import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils import obj_utils, time_utils
from leettools.core.consts.article_type import ArticleType
from leettools.core.consts.display_type import DisplayType
from leettools.flow.schemas.article import ArticleSectionPlan


# Note that even if we use the context expansion, the position_in_doc, start_offset
# and end_offset fields are still the values of the original segement.
class AnswerSource(BaseModel):
    """
    The source of the answer. This class is used to construct the reference list.
    """

    source_document_uuid: str = Field(..., description="UUID of the source document")
    source_uri: str = Field(..., description="URI of the source document")
    source_content: str = Field(..., description="content of the reference")
    score: float = Field(..., description="score of the reference")
    position_in_doc: str = Field(..., description="position in the document.")
    start_offset: int = Field(..., description="start offset of the reference")
    end_offset: int = Field(..., description="end offset of the reference")
    original_uri: Optional[str] = Field(None, description="original URI of the source")


class SourceItem(BaseModel):
    index: int = Field(..., description="index of the source item in the source list")
    source_segment_id: str = Field(..., description="source segment id")
    answer_source: AnswerSource = Field(..., description="source of the answer")


class ChatAnswerItemCreate(BaseModel):
    chat_id: str = Field(..., description="chat id")
    query_id: str = Field(..., description="query id")
    answer_content: str = Field(
        ...,
        description="aggregated MD format for the result",
    )
    answer_plan: Optional[ArticleSectionPlan] = Field(
        None, description="section plan for the answer"
    )
    # Right now the position_in_answer can only have two types of values
    # "all": means the answer is the aggregated answer of all the answer items
    # "1", "2", "3", ...: means the answer is a detailed section
    # there is no subsections for now
    position_in_answer: Optional[str] = Field(
        None, description="position of the item in the answer."
    )
    answer_title: Optional[str] = Field(None, description="title of the answer section")
    answer_score: Optional[float] = Field(None, description="score of the answer")

    # the key is the source_segment_id and the value is the SourceItem
    answer_source_items: Optional[Dict[str, SourceItem]] = Field(
        {}, description="source items for the answer"
    )

    position_layer: Optional[int] = Field(
        1, description="position layer of the section, placeholder for future use"
    )
    position_index: Optional[int] = Field(
        None, description="position index of the answer in the same layer"
    )
    position_heading: Optional[bool] = Field(
        True, description="whether the section has a heading"
    )

    display_type: Optional[DisplayType] = Field(
        None, description="how to display the section, used by the frontend"
    )
    user_data: Optional[Dict[str, Any]] = Field(
        None, description="custom data for the section, used by the frontend"
    )


class ChatAnswerItem(ChatAnswerItemCreate):
    answer_id: str = Field(..., description="answer id")
    created_at: datetime = Field(..., description="created time")
    updated_at: Optional[datetime] = Field(None, description="updated time")

    @classmethod
    def from_answer_create(
        ChatAnswerItem, answer_create: ChatAnswerItemCreate
    ) -> "ChatAnswerItem":
        ct = time_utils.current_datetime()
        answer = ChatAnswerItem(
            chat_id=answer_create.chat_id,
            query_id=answer_create.query_id,
            answer_id=str(uuid.uuid4()),
            answer_content=answer_create.answer_content,
            created_at=ct,
            updated_at=ct,
        )
        obj_utils.assign_properties(answer_create, answer)
        return answer


class ChatQueryResultCreate(BaseModel):
    """
    This is the raw result returned from the chat API client.

    Each answer item is considered as a section in the final answer.
    Thet should be presented in the order of the query.

    To make it backward compatible, right now the first item (index 0) will be still
    the aggregated answer of all the answer items and its answer source is the same
    as the global answer source. Detailed sections will begin from index 1.
    """

    chat_answer_item_create_list: List[ChatAnswerItemCreate] = Field(
        ..., description="The list of answer items to create"
    )
    global_answer_source_items: Optional[Dict[str, SourceItem]] = Field(
        None, description="The global answer source items"
    )
    article_type: Optional[str] = Field(
        ArticleType.CHAT.value, description="The article type for the chat."
    )


class ChatQueryResult(BaseModel):
    """
    After we add ChatQueryResultCreate to the database, we return this final result to
    the user.

    We added kb_name and kb_id to the result since it is possible that ChatQueryCreate
    is submitted with no kb and we have to create an adhoc kb for it.
    """

    chat_answer_item_list: List[ChatAnswerItem] = Field(
        ..., description="The list of answer items"
    )
    article_type: str = Field(None, description="The article type")
    global_answer_source_items: Optional[Dict[str, SourceItem]] = Field(
        None, description="The global answer source items"
    )
    kb_name: str = Field(..., description="The name of the knowledge base")
    kb_id: str = Field(..., description="The id of the knowledge base")
