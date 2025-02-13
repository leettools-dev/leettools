import os
from typing import List, Optional, Tuple

import aiofiles
from fastapi import Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from leettools.chat.history_manager import AbstractHistoryManager, get_history_manager
from leettools.chat.schemas.chat_history import ChatHistory, CHCreate, CHUpdate
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.log_location import LogLocator
from leettools.core.consts import flow_option
from leettools.core.knowledgebase.kb_manager import get_kb_name_from_query
from leettools.core.schemas.chat_query_item import ChatQueryItemCreate
from leettools.core.schemas.chat_query_options import ChatQueryOptions
from leettools.core.schemas.chat_query_result import ChatQueryResult
from leettools.core.schemas.knowledgebase import KBCreate, KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy import Strategy, StrategyBase
from leettools.flow.flow_manager import FlowManager
from leettools.svc.api_router_base import APIRouterBase


class QueryProgress(BaseModel):

    org_name: Optional[str] = None
    kb_name: Optional[str] = None
    user_name: Optional[str] = None
    query: Optional[str] = None
    chat_id: Optional[str] = None
    query_id: Optional[str] = None
    current_step: Optional[str] = None
    all_steps: Optional[List[str]] = None
    chat_query_result: Optional[ChatQueryResult] = None


class ChatRouter(APIRouterBase):
    """
    This class implements the router for the chat history and chat message endpoints.
    """

    def _setup_query(
        self,
        user: User,
        chat_query_item_create: ChatQueryItemCreate,
        org_name: Optional[str] = None,
        kb_name: Optional[str] = None,
        chat_query_options: Optional[ChatQueryOptions] = None,
        strategy_id: Optional[str] = None,
        strategy_base: Optional[StrategyBase] = None,
    ) -> Tuple[Org, KnowledgeBase, User, Strategy]:
        if org_name is None or org_name == "":
            org = self.org_manager.get_default_org()
        else:
            org = self.org_manager.get_org_by_name(org_name)
            if org is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=org_name, entity_type="Organization"
                )

        query = chat_query_item_create.query_content
        if query is None or query == "":
            raise exceptions.InvalidValueException(
                name="chat_query_item_create.query_content",
                expected="a non-empty string",
                actual=query,
            )

        if kb_name is None or kb_name == "":
            kb_name = get_kb_name_from_query(query)
            context = self.context
            settings = self.context.settings
            # if the kb already exists, an exception will be raised
            kb = self.kb_manager.add_kb(
                org=org,
                kb_create=KBCreate(
                    name=kb_name,
                    description=f"Created automatically by query: {query}",
                    user_uuid=user.user_uuid,
                    auto_schedule=False,
                    enable_contextual_retrieval=settings.ENABLE_CONTEXTUAL_RETRIEVAL,
                ),
            )
        else:
            kb = self.kb_manager.get_kb_by_name(org, kb_name)
            if kb is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=f"{org.name}/{kb_name}", entity_type="KnowledgeBase"
                )

        flow_type = chat_query_item_create.flow_type
        if flow_type is None or flow_type == "":
            flow_type = self.flow_manager.get_default_flow_type()

        flow = self.flow_manager.get_flow_by_type(flow_type)

        if strategy_id is not None:
            if strategy_base is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot specify both strategy_id and strategy_base.",
                )
            else:
                strategy = self.strategy_store.get_strategy_by_id(strategy_id)
        else:
            if strategy_base is not None:
                if strategy_base.strategy_sections is not None:
                    strategy = Strategy.get_dynamic_strategy(strategy_base)
                else:
                    logger().info(
                        "No strategy sections pecified, using default strategy."
                    )
                    strategy = self.strategy_store.get_default_strategy()
            else:
                logger().info("No strategy specified, using default strategy.")
                strategy = self.strategy_store.get_default_strategy()

        if chat_query_item_create.chat_id is None:
            chat_history = self.chat_manager.add_ch_entry(
                CHCreate(
                    name=query,
                    org_id=org.org_id,
                    kb_id=kb.kb_id,
                    creator_id=user.username,
                    article_type=flow.get_article_type(),
                )
            )
            chat_query_item_create.chat_id = chat_history.chat_id
        return org, kb, strategy

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        self.chat_manager: AbstractHistoryManager = get_history_manager(context)
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.strategy_store = context.get_strategy_store()
        self.user_store = context.get_user_store()
        self.user_settings_store = context.get_user_settings_store()
        self.flow_manager = FlowManager(context.settings)

        async def read_log_file(file_path: str):
            async with aiofiles.open(file_path, mode="rb") as file:
                while True:
                    chunk = await file.read(4096)  # Read in chunks of 4KB
                    if not chunk:
                        break
                    yield chunk

        @self.get("/stream_logs/{chat_id}/{query_id}")
        async def stream_log(
            chat_id: str,
            query_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> StreamingResponse:
            log_location = LogLocator.get_log_dir_for_query(
                chat_id=chat_id, query_id=query_id
            )
            log_path = log_location + "/query.log"
            try:
                if not os.path.isfile(log_path):
                    raise FileNotFoundError(f"Log file {log_path} not found.")
                return StreamingResponse(
                    read_log_file(log_path), media_type="text/plain"
                )
            except FileNotFoundError:
                raise HTTPException(
                    status_code=404, detail=f"Log file {log_path} not found."
                )
            except Exception as e:
                logger().error(f"Error while streaming log file: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Error while streaming log file: {e}"
                )

        @self.get("/logs/{chat_id}/{query_id}", response_class=PlainTextResponse)
        async def read_log(
            chat_id: str,
            query_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            log_location = LogLocator.get_log_dir_for_query(
                chat_id=chat_id, query_id=query_id
            )
            log_path = log_location + "/query.log"
            try:
                with open(log_path, "r") as file:
                    return file.read()
            except FileNotFoundError:
                raise HTTPException(
                    status_code=404, detail="Log file {log_path} not found."
                )

        @self.get("/history", response_model=List[ChatHistory])
        async def list_chat_history(
            list_only: Optional[bool] = False,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[ChatHistory]:
            """
            Get chat history by user
            """

            chat_history_list = self.chat_manager.get_ch_entries_by_username(
                calling_user.username
            )
            if list_only == True:
                for ch in chat_history_list:
                    ch.queries = []
                    ch.answers = []
            return chat_history_list

        @self.get("/articles", response_model=List[ChatHistory])
        async def list_articles(
            article_type: Optional[str] = None,
            org_name: Optional[str] = None,
            kb_name: Optional[str] = None,
            list_only: Optional[bool] = False,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[ChatHistory]:
            """
            Get articles for the current calling user.

            Args:
            - article_type: The type of article to retrieve. If not set of set to ""
                or "all", all types of articles are retrieved.
            - org_name: The name of the organization to retrieve articles from.
            - kb_name: The name of the knowledge base to retrieve articles from.
            - list_only: If True, only return the list of articles without the queries
                and answers.
            - calling_user: The calling user by dependency injection.

            Returns:
            - A list of articles with the target type.
            """

            if org_name is None or org_name == "":
                org = self.org_manager.get_default_org()
            else:
                org = self.org_manager.get_org_by_name(org_name)
                if org is None:
                    raise exceptions.EntityNotFoundException(
                        entity_name=org_name, entity_type="Org"
                    )

            if kb_name is None or kb_name == "":
                kb = None
            else:
                kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
                if kb is None:
                    raise exceptions.EntityNotFoundException(
                        entity_name=kb_name, entity_type="KnowledgeBase"
                    )

            if kb is not None and org is not None:
                if self.auth.can_read_kb(org=org, kb=kb, user=calling_user) is False:
                    raise HTTPException(
                        status_code=403,
                        detail=f"User {calling_user.username} does not have access to KB {kb_name}",
                    )

            if article_type is None or article_type == "" or article_type == "all":
                target_article_type = None
            else:
                target_article_type = article_type

            chat_history_list = (
                self.chat_manager.get_ch_entries_by_username_with_type_in_kb(
                    username=calling_user.username,
                    article_type=target_article_type,
                    org=org,
                    kb=kb,
                )
            )
            if list_only == True:
                for ch in chat_history_list:
                    ch.queries = []
                    ch.answers = []
            return chat_history_list

        @self.get("/history/{chat_id}", response_model=Optional[ChatHistory])
        async def get_chat_history_by_id(
            chat_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Optional[ChatHistory]:
            """
            Get chat history by user and chat id.

            Args:
            - chat_id: The ID of the chat history to retrieve.
            - calling_user_dict: The current user dictionary by dependency injection.

            Returns:
            - The chat history object. None if not found.
            """

            chat_history = self.chat_manager.get_ch_entry(
                calling_user.username, chat_id
            )
            if chat_history is None:
                return None

            if chat_history.org_id is None:
                org = self.org_manager.get_default_org()
                chat_history.org_id = org.org_id
            else:
                org = self.org_manager.get_org_by_id(chat_history.org_id)

            if chat_history.kb_name is None:
                if chat_history.kb_id is None or chat_history.kb_id == "":
                    logger().warning(
                        f"Chat history {chat_id} does not have a kb_id or kb_name."
                    )
                else:
                    kb = self.kb_manager.get_kb_by_id(org=org, kb_id=chat_history.kb_id)
                    chat_history.kb_name = kb.name

            return chat_history

        @self.get("/shared/{username}/{chat_id}", response_model=Optional[ChatHistory])
        async def get_shared_chat_history_by_id(
            username: str,
            chat_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Optional[ChatHistory]:
            """
            Get chat history by user and chat id
            """

            chat_history = self.chat_manager.get_ch_entry(username, chat_id)
            if chat_history is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=chat_id, entity_type="ChatHistory"
                )
            if chat_history.share_to_public is False:
                raise HTTPException(
                    status_code=403,
                    detail=f"The requested item {chat_id} from user {username} is not shared to public.",
                )
            return chat_history

        @self.put("/history/{chat_id}", response_model=ChatHistory)
        async def update_chat_history_new(
            chat_id: str,
            ch_update: CHUpdate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> ChatHistory:

            if ch_update.chat_id != chat_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Chat ID in the URL {chat_id} does not match the chat ID in "
                    f"the request body {ch_update.chat_id}",
                )
            if ch_update.creator_id != calling_user.username:
                raise HTTPException(
                    status_code=400,
                    detail=f"User name {calling_user.username} does not match the creator "
                    f"ID in the request body {ch_update.creator_id}",
                )
            chat_history = self.chat_manager.update_ch_entry(ch_update)
            return chat_history

        @self.post("/share/{chat_id}", response_model=Optional[ChatHistory])
        async def share_chat_history(
            chat_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Optional[ChatHistory]:

            ch = self.chat_manager.get_ch_entry(calling_user.username, chat_id)
            if ch is None:
                logger().warning(
                    f"Chat history with ID {chat_id} for user {calling_user.username} not found."
                )
                return None
            if ch.creator_id != calling_user.username:
                raise HTTPException(
                    status_code=400,
                    detail=f"User name {calling_user.username} cannot share the chat history "
                    f"owned by {ch.creator_id}",
                )
            ch.share_to_public = True
            chat_history = self.chat_manager.update_ch_entry(ch)
            return chat_history

        @self.post("/unshare/{chat_id}", response_model=Optional[ChatHistory])
        async def unshare_chat_history(
            chat_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Optional[ChatHistory]:

            ch = self.chat_manager.get_ch_entry(calling_user.username, chat_id)
            if ch is None:
                logger().warning(
                    "Chat history with ID {chat_id} for user {user.username} not found."
                )
                return None
            if ch.creator_id != calling_user.username:
                raise HTTPException(
                    status_code=400,
                    detail=f"User name {calling_user.username} cannot unshare the chat history "
                    f"owned by {ch.creator_id}",
                )
            ch.share_to_public = False
            chat_history = self.chat_manager.update_ch_entry(ch)
            return chat_history

        @self.post("/", response_model=ChatHistory)
        async def create_chat_history(
            ch_create: CHCreate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> ChatHistory:
            """
            Create chat history
            """
            if self.settings.SINGLE_USER_MODE is False:
                if calling_user.username != ch_create.creator_id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Creator ID in the URL {calling_user.username} does not match the creator "
                        f"ID in the request body {ch_create.creator_id}",
                    )

            org = self.org_manager.get_org_by_id(ch_create.org_id)
            if org is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=ch_create.org_id, entity_type="Organization"
                )

            kb_name = None
            if ch_create.kb_id is None or ch_create.kb_id == "":
                if ch_create.description is None or ch_create.description == "":
                    query = ch_create.name
                else:
                    query = ch_create.description

                kb_name = get_kb_name_from_query(query)
                # if the kb already exists, an exception will be raised
                settings = self.context.settings
                kb = self.kb_manager.add_kb(
                    org=org,
                    kb_create=KBCreate(
                        name=kb_name,
                        description=f"Created automatically by query: {query}",
                        user_uuid=calling_user.user_uuid,
                        auto_schedule=False,
                        enable_contextual_retrieval=settings.ENABLE_CONTEXTUAL_RETRIEVAL,
                    ),
                )
                ch_create.kb_id = kb.kb_id
                kb_name = kb.name
            else:
                kb = self.kb_manager.get_kb_by_id(org=org, kb_id=ch_create.kb_id)
                if kb is None:
                    raise exceptions.EntityNotFoundException(
                        entity_name=ch_create.kb_id, entity_type="KnowledgeBase"
                    )
                kb_name = kb.name

            chat_history = self.chat_manager.add_ch_entry(ch_create)
            chat_history.kb_name = kb_name
            return chat_history

        @self.delete("/history/{chat_id}")
        async def delete_chat_history_new(
            chat_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> None:
            """
            Delete chat history
            """

            self.chat_manager.delete_ch_entry(calling_user.username, chat_id)

        @self.delete("/history/{chat_id}/{query_id}")
        async def delete_chat_history_item_new(
            chat_id: str,
            query_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> None:
            """
            Delete chat history item
            """

            self.chat_manager.delete_ch_entry_item(
                calling_user.username, chat_id, query_id
            )

        @self.post("/get_answer", response_model=ChatQueryResult)
        def get_answer_for_query(
            chat_query_item_create: ChatQueryItemCreate,
            org_name: Optional[str] = None,
            kb_name: Optional[str] = None,
            chat_query_options: Optional[ChatQueryOptions] = None,
            strategy_id: Optional[str] = None,
            strategy_base: Optional[StrategyBase] = None,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> ChatQueryResult:
            """
            Get answer for the query user provides. By default we only return one answer,
            but sometimes we may return multiple answers for the user to choose.

            If we specify a strategy_id, we will use the strategy with that ID. If we specify
            a strategy_base, we will create a dynamic strategy with the base and use it.
            If both strategy_id and strategy_base are specified, we will raise an error.

            Args:
            - chat_query_item_create: The query item to create.
            - org_name: The name of the organization to retrieve articles from.
            - kb_name: The name of the knowledge base to use. If empty, an adhoc kb will be created.
            - chat_query_options: The options for the chat query.
            - strategy_id: The ID of the strategy to use.
            - strategy_base: The base of the strategy to use for dynamic strategy creation.
            - calling_user_dict: The current user dictionary by dependency injection.

            Returns:
            - The result of the query execution.
            """

            if chat_query_options is None:
                chat_query_options = ChatQueryOptions()
            if chat_query_options.flow_options is None:
                chat_query_options.flow_options = {}

            dm = flow_option.FLOW_OPTION_DISPLAY_MODE
            if chat_query_options.flow_options.get(dm, None) is None:
                chat_query_options.flow_options[dm] = "web"

            org, kb, strategy = self._setup_query(
                user=calling_user,
                chat_query_item_create=chat_query_item_create,
                org_name=org_name,
                kb_name=kb_name,
                chat_query_options=chat_query_options,
                strategy_id=strategy_id,
                strategy_base=strategy_base,
            )

            chat_query_result = self.chat_manager.run_query_with_strategy(
                org=org,
                kb=kb,
                user=calling_user,
                chat_query_item_create=chat_query_item_create,
                chat_query_options=chat_query_options,
                strategy=strategy,
            )
            if chat_query_result.kb_name is None:
                chat_query_result.kb_name = kb.name
            if chat_query_result.kb_id is None:
                chat_query_result.kb_id = kb.kb_id
            return chat_query_result
