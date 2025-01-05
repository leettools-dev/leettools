import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from leettools.common import exceptions
from leettools.common.logging import EventLogger, logger
from leettools.common.utils import obj_utils, time_utils
from leettools.core.schemas.chat_query_options import ChatQueryOptions
from leettools.core.strategy.schemas.strategy import Strategy, StrategyBase
from leettools.core.strategy.schemas.strategy_status import StrategyStatus
from leettools.core.strategy.strategy_store import AbstractStrategyStore

"""
See [README](./README.md) about the usage of different pydantic models.
"""

DUMMY_QUERY_ID = "dummy_query_id"
DUMMY_QUERY_CONTENT = "dummy_query_content"


class ChatQueryItemCreate(BaseModel):
    query_content: str = Field(..., description="The content of the query.")
    flow_type: Optional[str] = Field(
        None,
        description="The flow type of the query. Default is None, using system default.",
    )
    chat_id: Optional[str] = Field(
        None,
        description=(
            "The chat id of the chat history that the query belongs to. It can "
            "be None for new chats.",
        ),
    )


# right now ChatQueryItem does not have separate ChatQueryItemInDB schema
# which is causing some problems in the code
# for example: we need to recreate the strategy from the strategy_id and strategy_version
class ChatQueryItem(ChatQueryItemCreate):
    query_id: str = Field(..., description="The unique identifier of the query.")
    created_at: datetime = Field(
        ..., description="The timestamp when the query is created."
    )
    finished_at: Optional[datetime] = Field(
        None, description="The timestamp when the query is finished."
    )
    chat_query_options: Optional[ChatQueryOptions] = Field(
        None, description="The options for the query."
    )
    strategy_id: Optional[str] = Field(
        None,
        description="The strategy id for the query if a predefined strategy is used.",
    )
    strategy_base: Optional[StrategyBase] = Field(
        None,
        description="The strategy base for the query if a dynamic strategy is used.",
    )

    @classmethod
    def from_query_create(cls, query_create: ChatQueryItemCreate) -> "ChatQueryItem":
        ct = time_utils.current_datetime()
        chat_query_item = cls(
            chat_id=query_create.chat_id,
            query_id=str(uuid.uuid4()),
            query_content=query_create.query_content,
            flow_type=query_create.flow_type,
            created_at=ct,
        )
        obj_utils.assign_properties(query_create, chat_query_item)
        return chat_query_item

    def get_chat_query_options(self) -> ChatQueryOptions:
        if self.chat_query_options is None:
            self.chat_query_options = ChatQueryOptions()
        return self.chat_query_options

    def get_strategy(
        self,
        strategy_store: AbstractStrategyStore,
        display_logger: Optional[EventLogger] = None,
    ) -> Strategy:
        if display_logger is None:
            display_logger = logger()

        strategy_id = self.strategy_id
        strategy_base = self.strategy_base

        if strategy_id is None:
            strategy = strategy_store.get_default_strategy()
            display_logger.debug("No strategy is provided. Using default strategy.")
            return strategy

        if strategy_id == Strategy.DYNAMIC_STRATEGY_ID:
            if strategy_base is None:
                raise exceptions.UnexpectedCaseException(
                    "Strategy base must be provided for dynamic strategy."
                )

            display_logger.debug(f"Using dynamic strategy.")

            strategy = Strategy.get_dynamic_strategy(strategy_base)
            return strategy

        if strategy_base is None:
            strategy = strategy_store.get_strategy_by_id(strategy_id)
            if strategy is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=strategy_id, entity_type="Strategy"
                )
            return strategy

        # now we have both strategy_id and strategy_base since we pass them in
        # separately. The ID maybe deleted, but we should still be able to recreate
        # the strategy.
        strategy = strategy_store.get_strategy_by_id(strategy_id)
        if strategy is None:
            display_logger.warning(
                f"The strategy {strategy_id} is not found. Recreating the strategy."
            )
            strategy = Strategy(
                strategy_id=strategy_id,
                strategy_sections=strategy_base.strategy_sections,
                strategy_name="",
                strategy_hash="",
                strategy_version="",
                strategy_status=StrategyStatus.ACTIVE.value,
                is_system=True,
            )
        return strategy
