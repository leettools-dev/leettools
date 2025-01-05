from typing import List

from leettools.chat.history_manager import get_history_manager
from leettools.chat.schemas.chat_history import ChatHistory, CHCreate, CHUpdate
from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_item import ChatQueryItem, ChatQueryItemCreate
from leettools.core.schemas.chat_query_options import ChatQueryOptions
from leettools.core.schemas.chat_query_result import (
    ChatAnswerItem,
    ChatAnswerItemCreate,
    ChatQueryResultCreate,
    SourceItem,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import UserCreate


def test_chat_manager():

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context

        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(context, org, kb)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)
            logger().info(f"Finished test for store_types: {store_types}")


def _test_function(context: Context, org: Org, kb: KnowledgeBase):

    user_store = context.get_user_store()
    strategy_store = context.get_strategy_store()
    user_store._reset_for_test()
    kb_id = kb.kb_id

    test_username = "test_user"
    test_user = user_store.create_user(UserCreate(username=test_username))
    test_user_uuid = test_user.user_uuid

    # make sure the singleton function is working
    chat_manager = get_history_manager(context)
    assert chat_manager is not None

    chat_manager3 = get_history_manager(context)
    assert chat_manager3 is not None
    assert chat_manager3 == chat_manager

    test_name = "test_kb"
    test_desc = "This is a test chat history entry."

    ch_create = CHCreate(
        name=test_name,
        org_id=org.org_id,
        kb_id=kb_id,
        description=test_desc,
        creator_id=test_user.username,
    )
    ch1 = chat_manager.add_ch_entry(ch_create)

    assert ch1.name == test_name
    assert ch1.kb_id == kb_id
    assert ch1.creator_id == test_user.username
    assert ch1.description == test_desc
    assert ch1.chat_id is not None
    assert ch1.created_at is not None
    assert ch1.updated_at is not None
    assert ch1.updated_at == ch1.created_at

    query_create: ChatQueryItemCreate = ChatQueryItemCreate(
        query_content="What is the meaning of life?",
        chat_id=ch1.chat_id,
        flow_type="dummy",
    )

    strategy = strategy_store.get_default_strategy()
    if strategy is None:
        raise ValueError("No default strategy found.")

    chat_query_item: ChatQueryItem = chat_manager.add_query_item_to_chat(
        username=test_username,
        chat_query_item_create=query_create,
        chat_query_options=None,
        strategy=strategy,
    )
    assert chat_query_item is not None

    assert chat_query_item.query_content == query_create.query_content
    assert chat_query_item.chat_id == query_create.chat_id
    assert chat_query_item.created_at is not None
    assert chat_query_item.query_id is not None

    answer_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        answer_content="42 is the answer.",
        answer_plan=None,
        query_id=chat_query_item.query_id,
    )

    chat_query_result_3 = chat_manager._add_answers_to_chat(
        org=org,
        kb=kb,
        username=test_username,
        chat_query_item=chat_query_item,
        chat_query_result_create=ChatQueryResultCreate(
            chat_answer_item_create_list=[answer_create],
            global_answer_source_items={},
            article_type=ArticleType.CHAT.value,
        ),
    )

    assert chat_query_result_3 is not None
    assert chat_query_result_3.chat_answer_item_list is not None
    assert len(chat_query_result_3.chat_answer_item_list) == 1
    assert chat_query_result_3.article_type == ArticleType.CHAT.value

    chat_anwer_item_list_3 = chat_query_result_3.chat_answer_item_list
    assert len(chat_anwer_item_list_3) == 1
    assert chat_anwer_item_list_3[0].answer_content == answer_create.answer_content

    ch3: ChatHistory = chat_manager.get_ch_entry(test_username, chat_query_item.chat_id)
    assert ch3.chat_id == ch1.chat_id
    assert len(ch3.answers) == 1
    ai_3: ChatAnswerItem = ch3.answers[0]
    assert ai_3.answer_content == answer_create.answer_content
    assert ai_3.chat_id == answer_create.chat_id
    assert ai_3.query_id == chat_query_item.query_id
    assert ai_3.answer_id is not None
    assert ai_3.created_at is not None
    qi_3: ChatQueryItem = ch3.queries[0]
    assert qi_3.finished_at is not None
    assert qi_3.finished_at >= ai_3.created_at

    ch4: ChatHistory = chat_manager.get_ch_entry(
        username=test_username,
        chat_id=ch1.chat_id,
    )
    assert ch4.chat_id == ch1.chat_id
    assert len(ch4.queries) == 1
    assert len(ch4.answers) == 1
    assert ch4.queries[0].query_id == chat_query_item.query_id
    assert ch4.answers[0].answer_id == ai_3.answer_id
    assert ch4.answers[0].query_id == chat_query_item.query_id
    assert ch4.updated_at >= ai_3.created_at

    test_query_2 = "What is the airspeed velocity of an unladen swallow?"
    chat_query_result = chat_manager.run_query_with_strategy(
        org=org,
        kb=kb,
        user=test_user,
        chat_query_item_create=ChatQueryItemCreate(
            query_content=test_query_2,
            chat_id=ch1.chat_id,
            flow_type="dummy",
        ),
        chat_query_options=ChatQueryOptions(),
        strategy=strategy,
    )
    answer_item_list: List[ChatAnswerItem] = chat_query_result.chat_answer_item_list
    answer_item = answer_item_list[0]

    assert answer_item.answer_content is not None
    assert answer_item.created_at is not None
    assert answer_item.query_id is not None
    assert answer_item.query_id != chat_query_item.query_id

    source_list = answer_item.answer_source_items
    assert len(source_list) == 1
    source_item: SourceItem = list(source_list.values())[0]
    assert source_item.index is not None
    assert source_item.source_segment_id is not None
    assert source_item.answer_source.source_content is not None

    ch_update = CHUpdate(
        creator_id=ch1.creator_id,
        org_id=ch1.org_id,
        kb_id=ch1.kb_id,
        chat_id=ch1.chat_id,
        name="new_name",
        description="new_desc",
    )
    ch_updated = chat_manager.update_ch_entry(ch_update)
    assert ch_updated.name == ch_update.name
    assert ch_updated.description == ch_update.description
    assert ch_updated.chat_id == ch1.chat_id
    assert ch_updated.creator_id == ch1.creator_id

    ch_update_retrieved = chat_manager.get_ch_entry(
        username=test_username, chat_id=ch1.chat_id
    )
    assert ch_update_retrieved.name == ch_update.name
    assert ch_update_retrieved.description == ch_update.description
    assert ch_update_retrieved.chat_id == ch1.chat_id
    assert ch_update_retrieved.creator_id == ch1.creator_id

    found_query = False
    found_answer = False
    for query in ch_update_retrieved.queries:
        if query.query_id == chat_query_item.query_id:
            found_query = True
            break
    for answer in ch_update_retrieved.answers:
        if answer.query_id == chat_query_item.query_id:
            found_answer = True
            break
    assert found_query == True
    assert found_answer == True

    # test removal
    chat_manager.delete_ch_entry_item(
        username=test_username, chat_id=ch1.chat_id, query_id=chat_query_item.query_id
    )
    ch_delete_retrieved = chat_manager.get_ch_entry(
        username=test_username, chat_id=ch1.chat_id
    )
    found_query = False
    found_answer = False
    for query in ch_delete_retrieved.queries:
        if query.query_id == chat_query_item.query_id:
            found_query = True
            break
    for answer in ch_delete_retrieved.answers:
        if answer.query_id == chat_query_item.query_id:
            found_answer = True
            break
    assert found_query == False
    assert found_answer == False
