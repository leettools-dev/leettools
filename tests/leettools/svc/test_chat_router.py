from fastapi import HTTPException
from fastapi.testclient import TestClient

from leettools.chat.schemas.chat_history import ChatHistory, CHCreate, CHUpdate
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.article_type import ArticleType
from leettools.core.knowledgebase.kb_manager import get_kb_name_from_query
from leettools.core.schemas.chat_query_item import ChatQueryItemCreate
from leettools.core.schemas.chat_query_result import ChatQueryResult
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.settings import preset_store_types_for_tests
from leettools.svc.api.v1.routers.chat_router import ChatRouter
from leettools.svc.api.v1.routers.user_router import UserRouter


def test_chat_router_dynamic():

    for store_types in preset_store_types_for_tests():

        logger().info(f"Testing vector store dense with {store_types}")

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        EventLogger.set_global_default_level("INFO")

        org, kb, user = temp_setup.create_tmp_org_kb_user()
        router = ChatRouter()
        client = TestClient(router)

        try:
            _test_router(client, context, org, kb, user)
            _test_router_async(client, context, org, kb, user)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
):

    user_uuid = user.user_uuid
    username = user.username

    kb_manager = context.get_kb_manager()

    headers = {"username": username}

    response = client.get(f"/history", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0

    chat_create = CHCreate(
        name="Test Chat",
        kb_id=kb.kb_id,
        creator_id=username,
        org_id=org.org_id,
    )
    response = client.post("/", json=chat_create.model_dump(), headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    chat_history = ChatHistory.model_validate(response.json())
    assert chat_history.creator_id == username
    assert chat_history.chat_id is not None

    response = client.get(f"/history", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    for item in response.json():
        ch = ChatHistory.model_validate(item)
        assert ch.creator_id == username
        assert ch.chat_id == chat_history.chat_id
        assert ch.queries == []
        assert ch.answers == []

    response = client.get(f"/history?list_only=True", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    for item in response.json():
        ch = ChatHistory.model_validate(item)
        assert ch.creator_id == username
        assert ch.chat_id == chat_history.chat_id
        assert ch.queries == []
        assert ch.answers == []

    response = client.get(f"/history/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    ch = ChatHistory.model_validate(response.json())
    assert ch.creator_id == username
    assert ch.chat_id == chat_history.chat_id

    cqic = ChatQueryItemCreate(
        chat_id=chat_history.chat_id, query_content="Test Query", flow_type="dummy"
    )
    response = client.post(
        f"/get_answer?kb_name={kb.name}&org_name={org.name}",
        json={
            "chat_query_item_create": cqic.model_dump(),
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    chat_query_result = ChatQueryResult.model_validate(response.json())
    assert chat_query_result.chat_answer_item_list is not None
    assert len(chat_query_result.chat_answer_item_list) == 1
    answer_item = chat_query_result.chat_answer_item_list[0]
    # -1 means something went wrong in the query
    assert answer_item.answer_score != -1
    assert answer_item.answer_content is not None
    # the mock context won't have the answer for the question
    assert "This is a test report." in answer_item.answer_content

    try:
        response = client.get(
            f"/shared/{username}/{chat_history.chat_id}", headers=headers
        )
    except HTTPException as e:
        print(e.detail)
        assert e.status_code == 403

    response = client.get(f"/history", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    for item in response.json():
        ch = ChatHistory.model_validate(item)
        assert ch.creator_id == username
        assert ch.chat_id == chat_history.chat_id
        assert len(ch.queries) == 1
        assert len(ch.answers) == 1

    response = client.get(f"/history?list_only=True", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    for item in response.json():
        ch = ChatHistory.model_validate(item)
        assert ch.creator_id == username
        assert ch.chat_id == chat_history.chat_id
        assert ch.queries == []
        assert ch.answers == []

    ch_update = CHUpdate(
        chat_id=chat_history.chat_id,
        name="Test Chat Updated",
        description="Test Chat Description Updated",
        org_id=org.org_id,
        kb_id=kb.kb_id,
        creator_id=username,
    )
    response = client.put(
        f"/history/{chat_history.chat_id}",
        json=ch_update.model_dump(),
        headers=headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    ch = ChatHistory.model_validate(response.json())
    assert ch.creator_id == username
    assert ch.chat_id == chat_history.chat_id
    assert ch.name == ch_update.name
    assert ch.description == ch_update.description
    assert ch.article_type == ArticleType.CHAT

    response = client.get(f"/history/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    ch = ChatHistory.model_validate(response.json())
    assert ch.creator_id == username
    assert ch.chat_id == chat_history.chat_id
    assert ch.name == ch_update.name
    assert ch.description == ch_update.description

    response = client.get(f"/articles?article_type=chat", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    ch = ChatHistory.model_validate(response.json()[0])
    assert ch.creator_id == username
    assert ch.chat_id == chat_history.chat_id
    assert ch.name == ch_update.name
    assert ch.description == ch_update.description
    assert len(ch.queries) > 0
    assert len(ch.answers) > 0

    response = client.get(
        f"/articles?article_type=chat&list_only=True", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    ch = ChatHistory.model_validate(response.json()[0])
    assert ch.creator_id == username
    assert ch.chat_id == chat_history.chat_id
    assert ch.name == ch_update.name
    assert ch.description == ch_update.description
    assert len(ch.queries) == 0
    assert len(ch.answers) == 0

    chat_query_id = chat_query_result.chat_answer_item_list[0].query_id

    response = client.delete(
        f"/history/{chat_history.chat_id}/{chat_query_id}", headers=headers
    )
    assert response.status_code == 200

    chat_create2 = CHCreate(
        name="Test Chat 2",
        kb_id=kb.kb_id,
        creator_id=username,
        article_type=ArticleType.RESEARCH,
        org_id=org.org_id,
    )
    response = client.post("/", json=chat_create2.model_dump(), headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    chat_history2 = ChatHistory.model_validate(response.json())
    assert chat_history2.creator_id == username
    assert chat_history2.chat_id is not None
    assert chat_history2.article_type == ArticleType.RESEARCH

    # test create KB automatically
    cqic_2 = ChatQueryItemCreate(
        chat_id=chat_history2.chat_id,
        query_content="Test Query for new KB",
        flow_type="dummy",
    )
    new_kb_name = get_kb_name_from_query(cqic_2.query_content)
    assert new_kb_name.startswith("adhoc_")
    new_kb = kb_manager.get_kb_by_name(org, new_kb_name)
    assert new_kb is None

    response = client.post(
        f"/get_answer?org_name={org.name}",
        json={
            "chat_query_item_create": cqic_2.model_dump(),
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    chat_query_result = ChatQueryResult.model_validate(response.json())
    assert chat_query_result.chat_answer_item_list is not None

    new_kb = kb_manager.get_kb_by_name(org, new_kb_name)
    assert new_kb is not None
    assert new_kb.name == new_kb_name
    assert new_kb.kb_id is not None
    assert new_kb.description.startswith("Created automatically by query")
    assert new_kb.user_uuid == user_uuid

    # test create chat and kb automatically
    cqic_3 = ChatQueryItemCreate(query_content="XYZ ABC 123", flow_type="dummy")
    new_kb_name_3 = get_kb_name_from_query(cqic_3.query_content)
    assert new_kb_name_3.startswith("adhoc_")
    assert "XYZ_ABC" in new_kb_name_3
    new_kb_3 = kb_manager.get_kb_by_name(org, new_kb_name_3)
    assert new_kb_3 is None

    response = client.post(
        f"/get_answer?org_name={org.name}",
        json={
            "chat_query_item_create": cqic_3.model_dump(),
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    chat_query_result = ChatQueryResult.model_validate(response.json())
    assert chat_query_result.chat_answer_item_list is not None

    # test share to public
    response = client.get(f"/history/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    ch = ChatHistory.model_validate(response.json())
    assert ch.share_to_public == False

    response = client.post(f"/share/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200

    response = client.get(f"/shared/{username}/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    ch = ChatHistory.model_validate(response.json())
    assert ch.share_to_public == True
    assert ch.chat_id == chat_history.chat_id
    assert ch.article_type == ArticleType.CHAT

    response = client.get(f"/history/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    ch = ChatHistory.model_validate(response.json())
    assert ch.share_to_public == True

    user_router = UserRouter()
    user_client = TestClient(user_router)
    response = user_client.get(
        f"/shared/{username}/{ArticleType.CHAT.value}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    ch = ChatHistory.model_validate(response.json()[0])
    assert ch.share_to_public == True
    assert ch.chat_id == chat_history.chat_id

    response = user_client.get(
        f"/shared/{username}/{ArticleType.RESEARCH}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0

    try:
        response = client.post(
            f"/share/{chat_history.chat_id}", headers={"username": "admin"}
        )
    except Exception as e:
        assert "cannot share the chat history" in str(e)

    response = client.post(f"/unshare/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200

    response = client.get(f"/history/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    ch = ChatHistory.model_validate(response.json())
    assert ch.share_to_public == False

    response = user_client.get(
        f"/shared/{username}/{ArticleType.CHAT}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0

    # test deletions
    response = client.delete(f"/history/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200

    response = client.get(f"/history/{chat_history.chat_id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == None

    response = client.get(
        f"/logs/{chat_history.chat_id}/{chat_query_id}", headers=headers
    )
    assert response.status_code == 200
    result = response.read()
    print(result)
    assert " INFO " in str(result)

    # ideally we should use the async set up similar to test_job_router
    response = client.get(
        f"/stream_logs/{chat_history.chat_id}/{chat_query_id}", headers=headers
    )
    assert response.status_code == 200
    result = response.read()
    assert " INFO " in str(result)


def _test_router_async(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
):

    user_uuid = user.user_uuid
    username = user.username

    kb_manager = context.get_kb_manager()

    headers = {"username": username}

    cqic_4 = ChatQueryItemCreate(
        query_content="What can I do for you?", flow_type="dummy"
    )
    new_kb_name_4 = get_kb_name_from_query(cqic_4.query_content)
    assert new_kb_name_4.startswith("adhoc_")
    assert "What_can" in new_kb_name_4
    new_kb_4 = kb_manager.get_kb_by_name(org, new_kb_name_4)
    assert new_kb_4 is None
