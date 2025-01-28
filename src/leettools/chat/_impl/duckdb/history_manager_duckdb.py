import json
import traceback
import uuid
from functools import cmp_to_key
from typing import Any, Dict, List, Optional

from leettools.chat._impl.duckdb.chat_history_duckdb_schema import (
    ChatHistoryDuckDBSchema,
)
from leettools.chat._utils import position_util
from leettools.chat.history_manager import AbstractHistoryManager
from leettools.chat.schemas.chat_history import (
    ChatHistory,
    CHCreate,
    CHMetadata,
    CHUpdate,
)
from leettools.common import exceptions
from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.logging import logger, remove_logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.logging.logger_for_query import get_logger_for_chat
from leettools.common.utils import content_utils, time_utils
from leettools.context_manager import Context
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_item import ChatQueryItem, ChatQueryItemCreate
from leettools.core.schemas.chat_query_options import ChatQueryOptions
from leettools.core.schemas.chat_query_result import (
    ChatAnswerItem,
    ChatAnswerItemCreate,
    ChatQueryResult,
    ChatQueryResultCreate,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy import Strategy, StrategyBase
from leettools.flow.flow_manager import FlowManager


class HistoryManagerDuckDB(AbstractHistoryManager):
    """DuckDB implementation of the chat manager."""

    def __init__(self, context: Context):

        self.initialized = True
        self.context = context
        self.settings = context.settings
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.user_store = context.get_user_store()
        self.strategy_store = context.get_strategy_store()
        self.flow_manager = FlowManager(self.settings)
        self.duckdb_client = DuckDBClient(self.settings)

    def _add_answers_to_chat(
        self,
        org: Org,
        kb: KnowledgeBase,
        username: str,
        chat_query_item: ChatQueryItem,
        chat_query_result_create: ChatQueryResultCreate,
    ) -> ChatQueryResult:
        """
        Adds the answer items in the chat_query_result_create to the end of chat history.

        Args:
        - username: The username of the chat history entry.
        - chat_query_item: The chat query item to add the answers to.
        - chat_query_result_create: The chat query result to get the answers from.

        Returns:
        The created chat query result.
        """
        table_name = self._get_table_name_for_user(username)

        chat_id = chat_query_item.chat_id
        query_id = chat_query_item.query_id

        ch_in_db = self.get_ch_entry(username, chat_id)
        if ch_in_db is None:
            raise exceptions.EntityNotFoundException(
                entity_name=chat_id, entity_type="CHInDB"
            )

        chat_answer_item_list: List[ChatAnswerItem] = []
        for (
            chat_answer_item_create
        ) in chat_query_result_create.chat_answer_item_create_list:
            answer = ChatAnswerItem.from_answer_create(chat_answer_item_create)
            ch_in_db.answers.append(answer)
            chat_answer_item_list.append(answer)

        timestamp_now = time_utils.current_datetime()
        ch_in_db.updated_at = timestamp_now

        for query_item in ch_in_db.queries:
            if query_item.query_id == query_id:
                query_item.finished_at = timestamp_now
                break

        ch_in_db.metadata = self._get_ch_metadata(
            chat_query_item=chat_query_item, answers=chat_answer_item_list
        )
        query_dict = self._chat_history_to_dict(ch_in_db)
        column_list = [
            k
            for k in query_dict.keys()
            if k != ChatHistory.FIELD_CHAT_ID and k != ChatHistory.FIELD_CREATOR_ID
        ]
        value_list = [
            v
            for (k, v) in query_dict.items()
            if k != ChatHistory.FIELD_CHAT_ID and k != ChatHistory.FIELD_CREATOR_ID
        ]
        where_clause = f"WHERE {ChatHistory.FIELD_CHAT_ID} = ? AND {ChatHistory.FIELD_CREATOR_ID} = ?"
        value_list = value_list + [chat_id, username]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return ChatQueryResult(
            chat_answer_item_list=chat_answer_item_list,
            global_answer_source_items=chat_query_result_create.global_answer_source_items,
            article_type=chat_query_result_create.article_type,
            kb_name=kb.name,
            kb_id=kb.kb_id,
        )

    def _chat_history_to_dict(self, chat_history: ChatHistory) -> Dict[str, Any]:
        data = chat_history.model_dump()
        if (
            data.get(ChatHistory.FIELD_METADATA)
            and data[ChatHistory.FIELD_METADATA] != None
        ):
            data[ChatHistory.FIELD_METADATA] = CHMetadata.model_validate(
                data[ChatHistory.FIELD_METADATA]
            ).model_dump_json()
        else:
            data[ChatHistory.FIELD_METADATA] = "{}"
        if (
            data.get(ChatHistory.FIELD_QUERIES)
            and len(data[ChatHistory.FIELD_QUERIES]) > 0
        ):
            data[ChatHistory.FIELD_QUERIES] = (
                "["
                + ",".join(
                    ChatQueryItem.model_validate(q).model_dump_json()
                    for q in data[ChatHistory.FIELD_QUERIES]
                )
                + "]"
            )
        else:
            data[ChatHistory.FIELD_QUERIES] = "[]"
        if (
            data.get(ChatHistory.FIELD_ANSWERS)
            and len(data[ChatHistory.FIELD_ANSWERS]) > 0
        ):
            data[ChatHistory.FIELD_ANSWERS] = (
                "["
                + ",".join(
                    ChatAnswerItem.model_validate(a).model_dump_json()
                    for a in data[ChatHistory.FIELD_ANSWERS]
                )
                + "]"
            )
        else:
            data[ChatHistory.FIELD_ANSWERS] = "[]"
        return data

    def _create_answer_for_exception(
        self,
        chat_query_item: ChatQueryItem,
        display_logger: EventLogger,
        errmsg: str,
        trace: str,
    ) -> ChatQueryResultCreate:
        display_logger.error(
            f"Error in getting answer for query: {errmsg} \n\n {trace}"
        )

        if len(errmsg) > 200:
            errmsg = errmsg[:200] + " ...[truncated]"

        if len(trace) > 5000:
            trace = trace[:5000] + " ...[truncated]"

        if Context.EDS_CLI_CONTEXT_PREFIX in self.context.name:
            display_trace = trace
        else:
            display_trace = trace.replace("\n", "<br>")
        chat_answer_item_create_list = []

        # TODO: use a central place to handle i18n strings
        answer_content = (
            "Sorry, I am unable to answer the question because of a "
            f"backend error:\n\n{errmsg}\n\nPlease report to admin@leettools.com and "
            f"try again later. Error details:\n\n{display_trace}\n"
        )

        chat_answer_item_create = ChatAnswerItemCreate(
            chat_id=chat_query_item.chat_id,
            query_id=chat_query_item.query_id,
            answer_content=answer_content,
            answer_plan=None,
            answer_score=0,
        )
        chat_answer_item_create_list.append(chat_answer_item_create)
        return ChatQueryResultCreate(
            chat_answer_item_create_list=chat_answer_item_create_list
        )

    def _dict_to_chat_history(self, chat_dict: Dict[str, Any]) -> ChatHistory:
        metadata = None
        """Convert a dictionary to a ChatHistory object."""
        if (
            ChatHistory.FIELD_METADATA in chat_dict
            and chat_dict[ChatHistory.FIELD_METADATA] != "{}"
        ):
            metadata = CHMetadata.model_validate_json(
                chat_dict[ChatHistory.FIELD_METADATA]
            )
        queries = []
        if (
            ChatHistory.FIELD_QUERIES in chat_dict
            and chat_dict[ChatHistory.FIELD_QUERIES] != "[]"
        ):
            json_str = '{ "queries": ' + chat_dict[ChatHistory.FIELD_QUERIES] + "}"
            json_obj = json.loads(json_str)
            for query_dict in json_obj["queries"]:
                queries.append(ChatQueryItem.model_validate(query_dict))
        answers = []
        if (
            ChatHistory.FIELD_ANSWERS in chat_dict
            and chat_dict[ChatHistory.FIELD_ANSWERS] != "[]"
        ):
            json_str = '{ "answers": ' + chat_dict[ChatHistory.FIELD_ANSWERS] + "}"
            json_obj = json.loads(json_str)
            for answer_dict in json_obj["answers"]:
                answers.append(ChatAnswerItem.model_validate(answer_dict))

        chat_history = ChatHistory(
            chat_id=chat_dict[ChatHistory.FIELD_CHAT_ID],
            name=chat_dict[ChatHistory.FIELD_NAME],
            kb_id=chat_dict[ChatHistory.FIELD_KB_ID],
            creator_id=chat_dict[ChatHistory.FIELD_CREATOR_ID],
            article_type=ArticleType(chat_dict[ChatHistory.FIELD_ARTICLE_TYPE]),
            description=chat_dict[ChatHistory.FIELD_DESCRIPTION],
            share_to_public=chat_dict[ChatHistory.FIELD_SHARE_TO_PUBLIC],
            org_id=chat_dict[ChatHistory.FIELD_ORG_ID],
            owner_id=chat_dict[ChatHistory.FIELD_OWNER_ID],
            created_at=chat_dict[ChatHistory.FIELD_CREATED_AT],
            updated_at=chat_dict[ChatHistory.FIELD_UPDATED_AT],
            metadata=metadata,
            queries=queries,
            answers=answers,
            kb_name=chat_dict[ChatHistory.FIELD_KB_NAME],
        )
        return chat_history

    def _execute_flow_for_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: EventLogger,
    ) -> ChatQueryResultCreate:
        try:
            display_logger.debug(
                f"Getting answer for query: {chat_query_item.query_content}"
            )

            chat_query_options = chat_query_item.chat_query_options

            if chat_query_options is None:
                chat_query_options = ChatQueryOptions()
                display_logger.debug(
                    "No chat query options provided. Using default options."
                )
            else:
                display_logger.debug(
                    f"Using user-specified chat query options {chat_query_options}."
                )

            # here we only need the strategy type but forced to get the whole strategy obj

            strategy = chat_query_item.get_strategy(self.strategy_store, display_logger)
            if strategy is None:
                raise exceptions.UnexpectedCaseException(
                    "chat_query_item.get_strategy() returned None."
                )

            display_logger.debug(
                f"Using flow for flow type {chat_query_item.flow_type}"
            )
            if chat_query_item.flow_type is None:
                chat_query_item.flow_type = self.settings.DEFAULT_FLOW_TYPE
            flow = self.flow_manager.get_flow_by_type(chat_query_item.flow_type)
            return flow.execute_query(
                org=org,
                kb=kb,
                user=user,
                chat_query_item=chat_query_item,
                display_logger=display_logger,
            )
        except exceptions.EdsExceptionBase as leettools_exception:
            display_logger.debug("Getting a LeetTools exception.")
            errmsg = str(leettools_exception)
            trace = leettools_exception.exception_trace
            return self._create_answer_for_exception(
                chat_query_item=chat_query_item,
                display_logger=display_logger,
                errmsg=errmsg,
                trace=trace,
            )
        except Exception as e:
            display_logger.debug("Getting a general exception.")
            errmsg = str(e)
            trace = traceback.format_exc()
            return self._create_answer_for_exception(
                chat_query_item=chat_query_item,
                display_logger=display_logger,
                errmsg=errmsg,
                trace=trace,
            )

    def _get_ch_metadata(
        self, chat_query_item: ChatQueryItem, answers: List[ChatAnswerItem]
    ) -> CHMetadata:
        result_snippet = ""
        img_link = None

        for answer in answers:
            if answer.position_in_answer == "1":
                result_snippet = answer.answer_content[:200]
            if answer.position_in_answer == "all":
                if result_snippet == "":
                    result_snippet = answer.answer_content[:200]

            if img_link is None:
                img_link = content_utils.get_image_url(answer.answer_content)

        metadata = CHMetadata(
            flow_type=chat_query_item.flow_type,
            result_snippet=result_snippet,
            img_link=img_link,
        )
        return metadata

    def _get_table_name_for_user(self, username: str) -> str:
        user = self.user_store.get_user_by_name(username)
        db_name = User.get_user_db_name(user.user_uuid)
        return self.duckdb_client.create_table_if_not_exists(
            db_name,
            self.settings.COLLECTION_CHAT_HISTORY,
            ChatHistoryDuckDBSchema.get_schema(),
        )

    def _update_kb_timestamp(self, org: Org, kb: KnowledgeBase) -> None:
        try:
            self.kb_manager.update_kb_timestamp(org, kb)
        except Exception as e:
            logger().error(f"Error updating KB timestamp: {e}. Exception ignored.")

    def add_answer_item_to_chat(
        self,
        username: str,
        chat_id: str,
        query_id: str,
        position_in_answer: str,
        new_answer: ChatAnswerItemCreate,
    ) -> ChatHistory:
        ch_in_db = self.get_ch_entry(username, chat_id)
        if ch_in_db is None:
            raise exceptions.EntityNotFoundException(
                entity_name=chat_id, entity_type="ChatHistory"
            )

        for answer in ch_in_db.answers:
            if answer.query_id != query_id:
                continue
            if (
                position_util.compare_pos(position_in_answer, answer.position_in_answer)
                <= 0
            ):
                answer.position_in_answer = position_util.shift_down(
                    answer.position_in_answer, 1, int(position_in_answer)
                )

        new_answer_item = ChatAnswerItem.from_answer_create(new_answer)
        ch_in_db.answers.append(new_answer_item)

        # sort the answers by their position_in_answer
        # make sure the order is like
        # 1, 1.1, 1.2, 2, 2.1, 2.2, 3, 3.1, 3.2
        # TODO: right now all the position_in_answers are integers + "all"
        sorted_answers: List[ChatAnswerItem] = sorted(
            ch_in_db.answers, key=cmp_to_key(position_util.is_answer_item_before)
        )

        cur_index = 1
        for cai in sorted_answers:
            if answer.query_id != query_id:
                continue
            if cai.position_in_answer == "all":
                continue
            if cai.answer_score < 0:
                continue
            cai.position_in_answer = str(cur_index)
            cur_index += 1

        update_dict = {"answers": [answer.model_dump() for answer in sorted_answers]}
        column_list = list(update_dict.keys())
        value_list = list(update_dict.values())
        where_clause = f"WHERE {ChatHistory.FIELD_CHAT_ID} = ? AND {ChatHistory.FIELD_CREATOR_ID} = ?"
        value_list = value_list + [chat_id, username]
        table_name = self._get_table_name_for_user(username)
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        updated_ch = self.get_ch_entry(username, chat_id)
        if updated_ch is None:
            raise exceptions.UnexpectedOperationFailureException(
                operation_desc="Adding answer to chat history in DB",
                error="The newly updated chat history is None",
            )
        return updated_ch

    def add_ch_entry(self, ch_create: CHCreate) -> ChatHistory:
        """Add a new chat history entry."""
        chat_id = str(uuid.uuid4())
        current_time = time_utils.current_datetime()

        chat_dict = ch_create.model_dump()
        chat_dict.update(
            {
                ChatHistory.FIELD_CHAT_ID: chat_id,
                ChatHistory.FIELD_CREATED_AT: current_time,
                ChatHistory.FIELD_UPDATED_AT: current_time,
                ChatHistory.FIELD_QUERIES: "[]",
                ChatHistory.FIELD_ANSWERS: "[]",
                ChatHistory.FIELD_METADATA: "{}",
            }
        )

        column_list = list(chat_dict.keys())
        value_list = list(chat_dict.values())
        table_name = self._get_table_name_for_user(ch_create.creator_id)
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )
        return self.get_ch_entry(ch_create.creator_id, chat_id)

    def add_query_item_to_chat(
        self,
        username: str,
        chat_query_item_create: ChatQueryItemCreate,
        chat_query_options: ChatQueryOptions,
        strategy: Strategy,
    ) -> ChatQueryItem:
        chat_id = chat_query_item_create.chat_id
        ch_in_db = self.get_ch_entry(username, chat_id)
        if ch_in_db is None:
            raise exceptions.EntityNotFoundException(
                entity_name=chat_id, entity_type="ChatHistory"
            )
        chat_query_item = ChatQueryItem.from_query_create(chat_query_item_create)
        chat_query_item.chat_query_options = chat_query_options
        chat_query_item.strategy_id = strategy.strategy_id
        if strategy.strategy_id == Strategy.DYNAMIC_STRATEGY_ID:
            chat_query_item.strategy_base = StrategyBase(
                strategy_sections=strategy.strategy_sections,
            )

        ch_in_db.queries.append(chat_query_item)
        ch_in_db.updated_at = chat_query_item.created_at
        query_dict = self._chat_history_to_dict(ch_in_db)
        logger().info(f"ChatQueryItem: {query_dict}")
        column_list = [
            k
            for k in query_dict.keys()
            if k != ChatHistory.FIELD_CHAT_ID and k != ChatHistory.FIELD_CREATOR_ID
        ]
        value_list = [
            v
            for k, v in query_dict.items()
            if k != ChatHistory.FIELD_CHAT_ID and k != ChatHistory.FIELD_CREATOR_ID
        ]
        table_name = self._get_table_name_for_user(username)
        where_clause = f"WHERE {ChatHistory.FIELD_CHAT_ID} = ? AND {ChatHistory.FIELD_CREATOR_ID} = ?"
        value_list = value_list + [chat_id, username]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        rtn_ch_in_db = self.get_ch_entry(username, chat_id)
        if rtn_ch_in_db is not None:
            return chat_query_item
        else:
            raise exceptions.UnexpectedOperationFailureException(
                operation_desc="Adding query to chat history in DB",
                error="No return from update_one",
            )

    def delete_ch_entry(self, username: str, chat_id: str) -> None:
        """Delete a chat history entry."""
        table_name = self._get_table_name_for_user(username)
        where_clause = f"WHERE {ChatHistory.FIELD_CHAT_ID} = ? AND {ChatHistory.FIELD_CREATOR_ID} = ?"
        value_list = [chat_id, username]
        self.duckdb_client.delete_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )

    def delete_ch_entry_item(self, username: str, chat_id: str, query_id: str) -> None:
        ch_in_db = self.get_ch_entry(username, chat_id)
        if ch_in_db is None:
            raise exceptions.EntityNotFoundException(
                entity_name=chat_id, entity_type="ChatHistory"
            )

        for query_item in ch_in_db.queries:
            if query_item.query_id == query_id:
                ch_in_db.queries.remove(query_item)
        for answer_item in ch_in_db.answers:
            if answer_item.query_id == query_id:
                ch_in_db.answers.remove(answer_item)
        ch_in_db.updated_at = time_utils.current_datetime()
        query_dict = self._chat_history_to_dict(ch_in_db)
        column_list = [
            k
            for k in query_dict.keys()
            if k != ChatHistory.FIELD_CHAT_ID and k != ChatHistory.FIELD_CREATOR_ID
        ]
        value_list = [
            v
            for k, v in query_dict.items()
            if k != ChatHistory.FIELD_CHAT_ID and k != ChatHistory.FIELD_CREATOR_ID
        ]
        table_name = self._get_table_name_for_user(username)
        where_clause = f"WHERE {ChatHistory.FIELD_CHAT_ID} = ? AND {ChatHistory.FIELD_CREATOR_ID} = ?"
        value_list = value_list + [chat_id, username]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        rtn_ch_in_db = self.get_ch_entry(username, chat_id)
        if rtn_ch_in_db is None:
            raise exceptions.UnexpectedOperationFailureException(
                operation_desc="Deleting query from chat history in DB",
                error="No return from update_one",
            )

    def get_ch_entry(self, username: str, chat_id: str) -> Optional[ChatHistory]:
        """Get a chat history entry by ID."""
        table_name = self._get_table_name_for_user(username)
        where_clause = f"WHERE {ChatHistory.FIELD_CHAT_ID} = ? AND {ChatHistory.FIELD_CREATOR_ID} = ?"
        value_list = [chat_id, username]
        rtn_dict = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if rtn_dict is None:
            return None
        return self._dict_to_chat_history(rtn_dict)

    def get_ch_entries_by_username(self, username: str) -> List[ChatHistory]:
        """Get all chat history entries for a user."""
        table_name = self._get_table_name_for_user(username)
        where_clause = f"WHERE {ChatHistory.FIELD_CREATOR_ID} = ? ORDER BY {ChatHistory.FIELD_UPDATED_AT} DESC"
        value_list = [username]
        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_chat_history(rtn_dict) for rtn_dict in rtn_dicts]

    def get_ch_entries_by_username_with_type(
        self, username: str, article_type: str
    ) -> List[ChatHistory]:
        """Get chat history entries by type for a user."""
        table_name = self._get_table_name_for_user(username)
        where_clause = (
            f"WHERE {ChatHistory.FIELD_CREATOR_ID} = ? AND {ChatHistory.FIELD_ARTICLE_TYPE} = ?"
            f"ORDER BY {ChatHistory.FIELD_UPDATED_AT} DESC"
        )
        value_list = [username, article_type]
        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_chat_history(rtn_dict) for rtn_dict in rtn_dicts]

    def get_ch_entries_by_username_with_type_in_kb(
        self,
        username: str,
        article_type: Optional[str] = None,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
    ) -> list[ChatHistory]:
        query = {ChatHistory.FIELD_CREATOR_ID: username}
        if article_type is not None:
            query[ChatHistory.FIELD_ARTICLE_TYPE] = article_type
        if kb is not None:
            query[ChatHistory.FIELD_KB_ID] = kb.kb_id

        condition_clause = " AND ".join([f"{k} = ?" for k in query.keys()])
        where_clause = f"WHERE {condition_clause}"
        table_name = self._get_table_name_for_user(username)
        value_list = list(query.values())
        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_chat_history(rtn_dict) for rtn_dict in rtn_dicts]

    def get_kb_owner_ch_entries_by_type(
        self, org: Org, kb: KnowledgeBase, article_type: Optional[ArticleType] = None
    ) -> list[ChatHistory]:
        kb_owner_name = kb.get_owner_name()
        if kb_owner_name is None:
            raise exceptions.UnexpectedOperationFailureException(
                operation_desc="Getting owner for KB", error="Owner is None"
            )
        if article_type is None:
            query = {
                ChatHistory.FIELD_CREATOR_ID: kb_owner_name,
                ChatHistory.FIELD_KB_ID: kb.kb_id,
            }
        else:
            query = {
                ChatHistory.FIELD_CREATOR_ID: kb_owner_name,
                ChatHistory.FIELD_KB_ID: kb.kb_id,
                ChatHistory.FIELD_ARTICLE_TYPE: article_type.value,
            }
        table_name = self._get_table_name_for_user(kb_owner_name)
        where_clause = " AND ".join([f"{k} = ?" for k in query.keys()])
        where_clause = f"WHERE {where_clause}"
        value_list = list(query.values())
        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_chat_history(rtn_dict) for rtn_dict in rtn_dicts]

    def get_shared_samples_by_flow_type(
        self, org: Org, flow_type: str
    ) -> list[ChatHistory]:
        flow = self.flow_manager.get_flow_by_type(flow_type)
        article_type = flow.get_article_type()
        if article_type is None:
            raise exceptions.UnexpectedCaseException(
                f"Article type is None for flow type {flow_type}"
            )

        if self.settings.SHARE_SAMPLES_FROM_USERS is not None:
            share_from_users = self.settings.SHARE_SAMPLES_FROM_USERS.split(",")
        else:
            share_from_users = [User.ADMIN_USERNAME]

        all_article_list: List[ChatHistory] = []

        for username in share_from_users:
            username = username.strip()
            target_user = self.user_store.get_user_by_name(username)
            if target_user is None:
                logger().error(
                    f"User {username} specified in SHARE_SAMPLES_FROM_USERS not found."
                )
                continue

            try:
                article_list = self.get_ch_entries_by_username_with_type(
                    username=username,
                    article_type=article_type,
                )
                for article in article_list:
                    if not article.share_to_public:
                        continue
                    if article.metadata is None:
                        continue
                    if article.metadata.flow_type is None:
                        continue
                    if article.metadata.flow_type == flow_type:
                        all_article_list.append(article)
            except Exception as e:
                logger().error(
                    f"Error getting shared article entries for user {username}: {e}"
                )
                continue

        return all_article_list

    def remove_answer_item_from_chat(
        self,
        username: str,
        chat_id: str,
        query_id: str,
        position_in_answer: str,
    ) -> Optional[ChatHistory]:
        ch_in_db = self.get_ch_entry(username, chat_id)
        if ch_in_db is None:
            raise exceptions.EntityNotFoundException(
                entity_name=chat_id, entity_type="ChatHistory"
            )
        updated = False
        for answer in ch_in_db.answers:
            if answer.query_id != query_id:
                continue
            if answer.answer_score < 0:
                continue
            if answer.position_in_answer == position_in_answer:
                # tmp solution since we do not want to delete the old answer
                answer.answer_score = -2
                answer.query_id = "-" + answer.query_id + "-"
                answer.updated_at = time_utils.current_datetime()
                updated = True
                break

        if updated:
            # sort the answers by their position_in_answer
            # make sure the order is like
            # 1, 1.1, 1.2, 2, 2.1, 2.2, 3, 3.1, 3.2
            updated_answers: List[ChatAnswerItem] = sorted(
                ch_in_db.answers, key=cmp_to_key(position_util.is_answer_item_before)
            )

            cur_index = 1
            for cai in updated_answers:
                if answer.query_id != query_id:
                    continue
                if cai.position_in_answer == "all":
                    continue
                if cai.answer_score < 0:
                    continue
                cai.position_in_answer = str(cur_index)
                cur_index += 1

            update_dict = {
                "answers": [answer.model_dump() for answer in updated_answers]
            }
            column_list = [k for k in update_dict.keys()]
            value_list = [v for v in update_dict.values()]
            table_name = self._get_table_name_for_user(username)
            where_clause = f"WHERE {ChatHistory.FIELD_CHAT_ID} = ? AND {ChatHistory.FIELD_CREATOR_ID} = ?"
            value_list = value_list + [chat_id, username]
            self.duckdb_client.update_table(
                table_name=table_name,
                column_list=column_list,
                value_list=value_list,
                where_clause=where_clause,
            )
            return self.get_ch_entry(username, chat_id)
        else:
            logger().warning(
                f"No answer at position {position_in_answer} found to remove "
                f"for query {query_id} in chat {chat_id} for user {username}"
            )
            return None

    def run_query_with_strategy(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item_create: ChatQueryItemCreate,
        chat_query_options: Optional[ChatQueryOptions] = None,
        strategy: Optional[Strategy] = None,
        display_logger: Optional[EventLogger] = None,
    ) -> ChatQueryResult:
        if display_logger is None:
            display_logger = logger()

        if chat_query_options is None:
            chat_query_options = ChatQueryOptions()
            display_logger.info(
                "No chat query options provided. Using default options."
            )
        else:
            display_logger.info(
                f"Using user-specified chat query options {chat_query_options}."
            )

        if strategy is None:
            strategy = self.strategy_store.get_default_strategy()
            if strategy is None:
                raise exceptions.UnexpectedCaseException(
                    "No strategy is provided and no default strategy is found."
                )
            else:
                display_logger.info("No strategy is provided. Using default strategy.")

        chat_query_item: ChatQueryItem = self.add_query_item_to_chat(
            username=user.username,
            chat_query_item_create=chat_query_item_create,
            chat_query_options=chat_query_options,
            strategy=strategy,
        )

        return self.run_query_item(
            org=org,
            kb=kb,
            user=user,
            chat_query_item=chat_query_item,
        )

    def run_query_item(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
    ) -> ChatQueryResult:

        logger_name, query_logger = get_logger_for_chat(
            chat_id=chat_query_item.chat_id,
            query_id=chat_query_item.query_id,
        )

        try:
            query_logger.info(f"[Status]Query started: {chat_query_item.query_content}")
            chat_query_result_create: ChatQueryResultCreate = (
                self._execute_flow_for_query(
                    org=org,
                    kb=kb,
                    user=user,
                    chat_query_item=chat_query_item,
                    display_logger=query_logger,
                )
            )

            if chat_query_result_create is not None:
                query_logger.info("[Status]Saving results.")
                chat_query_result = self._add_answers_to_chat(
                    org=org,
                    kb=kb,
                    username=user.username,
                    chat_query_item=chat_query_item,
                    chat_query_result_create=chat_query_result_create,
                )

                query_logger.info("[Status]Query completed.")
                self._update_kb_timestamp(org, kb)
                return chat_query_result
            else:
                # chat_query_result_create is None
                query_logger.info("[Status]Query failed or not completed.")
                return None
        finally:
            remove_logger(logger_name)

    def update_ch_entry(self, ch_update: CHUpdate) -> Optional[ChatHistory]:
        """Update an existing chat history entry."""
        update_dict = {}
        if ch_update.name is not None:
            update_dict[ChatHistory.FIELD_NAME] = ch_update.name
        if ch_update.description is not None:
            update_dict[ChatHistory.FIELD_DESCRIPTION] = ch_update.description
        if ch_update.share_to_public is not None:
            update_dict[ChatHistory.FIELD_SHARE_TO_PUBLIC] = ch_update.share_to_public
        if update_dict == {}:
            logger().info("No update needed for chat history")
            return self.get_ch_entry(ch_update.creator_id, ch_update.chat_id)

        update_dict[ChatHistory.FIELD_UPDATED_AT] = time_utils.current_datetime()

        column_list = [k for k in update_dict.keys()]
        value_list = [v for v in update_dict.values()]
        table_name = self._get_table_name_for_user(ch_update.creator_id)
        where_clause = f"WHERE {ChatHistory.FIELD_CHAT_ID} = ? AND {ChatHistory.FIELD_CREATOR_ID} = ?"
        value_list = value_list + [ch_update.chat_id, ch_update.creator_id]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_ch_entry(ch_update.creator_id, ch_update.chat_id)

    def update_ch_entry_answer(
        self,
        username: str,
        chat_id: str,
        query_id: str,
        position_in_answer: str,
        new_answer: ChatAnswerItemCreate,
    ) -> Optional[ChatHistory]:
        """Update an existing chat with a new answer section."""
        # First, get the current chat history
        chat = self.get_ch_entry(username, chat_id)
        if not chat:
            raise exceptions.EntityNotFoundException(
                entity_name=f"Chat history {chat_id}", entity_type="ChatHistory"
            )
        updated = False
        for answer in chat.answers:
            if answer.query_id != query_id:
                continue
            if position_in_answer == answer.position_in_answer:
                # tmp solution since we do not want to delete the old answer
                answer.answer_score = -2
                answer.query_id = "-" + answer.query_id + "-"
                answer.updated_at = time_utils.current_datetime()
                new_answer = ChatAnswerItem.from_answer_create(new_answer)
                chat.answers.append(new_answer)
                updated = True
                break

        if updated:
            # sort the answers by their position_in_answer
            # make sure the order is like
            # 1, 1.1, 1.2, 2, 2.1, 2.2, 3, 3.1, 3.2
            updated_answers: List[ChatAnswerItem] = sorted(
                chat.answers,
                key=cmp_to_key(position_util.is_answer_item_before),
            )

            cur_index = 1
            for cai in updated_answers:
                if cai.query_id != query_id:
                    continue
                if cai.position_in_answer == "all":
                    continue
                if cai.answer_score < 0:
                    continue
                cai.position_in_answer = str(cur_index)
                cur_index += 1

            # we will just use the first ChatQueryItem to get the metadata
            # for QA_Chat, it is the firt query
            # for all the other types, there shoul be only one ChatQueryItem
            metadata = self._get_ch_metadata(
                chat_query_item=chat.queries[0], answers=updated_answers
            )

            update_dict = {
                "answers": [answer.model_dump() for answer in updated_answers],
                "metadata": metadata.model_dump(),
            }
            column_list = [k for k in update_dict.keys()]
            value_list = [v for v in update_dict.values()]
            table_name = self._get_table_name_for_user(username)
            where_clause = f"WHERE {ChatHistory.FIELD_CHAT_ID} = ? AND {ChatHistory.FIELD_CREATOR_ID} = ?"
            value_list = value_list + [chat_id, username]
            self.duckdb_client.update_table(
                table_name=table_name,
                column_list=column_list,
                value_list=value_list,
                where_clause=where_clause,
            )
            return self.get_ch_entry(username, chat_id)
        else:
            logger().warning(
                f"No answer at position {position_in_answer} found to update "
                f"for query {query_id} in chat {chat_id} for user {username}"
            )
            return None
