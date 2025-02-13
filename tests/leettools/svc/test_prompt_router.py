from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.prompt import (
    Prompt,
    PromptCategory,
    PromptCreate,
    PromptStatus,
    PromptType,
)
from leettools.svc.api.v1.routers.prompt_router import PromptRouter


def test_prompt_router():
    temp_setup = TempSetup()
    temp_setup.context.settings.DOC_STORE_TYPE = "duckdb"
    context = temp_setup.context

    org, kb, user = temp_setup.create_tmp_org_kb_user()
    prompt_store = context.get_prompt_store()

    router = PromptRouter()
    client = TestClient(router)

    try:
        _test_router(client, context, org, kb, user)
    finally:
        prompt_store._reset_for_test()
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
) -> None:

    prompt_store = context.get_prompt_store()
    assert prompt_store is not None

    admin_user = context.get_user_store().get_user_by_name(User.ADMIN_USERNAME)
    headers = {"username": admin_user.username}

    prompt_template = "test_prompt {{ test_var }}"
    prompt_category = PromptCategory.INTENTION
    prompt_type = PromptType.SYSTEM
    prompt_status = PromptStatus.PRODUCTION

    response = client.get(
        f"/?category={prompt_category.value}&type={prompt_type.value}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == len(
        prompt_store.list_prompts_by_filter(prompt_category, prompt_type, prompt_status)
    )

    response = client.get(f"/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == len(prompt_store.list_prompts())

    prompt_create = PromptCreate(
        prompt_category=prompt_category,
        prompt_type=prompt_type,
        prompt_template=prompt_template,
        prompt_variables={"test_var": "test_value"},
    )
    response = client.put("/", json=prompt_create.model_dump(), headers=headers)
    assert response.status_code == 200
    prompt = Prompt.model_validate(response.json())
    assert prompt.prompt_template == prompt_template
    assert prompt.prompt_category == prompt_category
    assert prompt.prompt_type == prompt_type
    assert prompt.prompt_variables == {"test_var": "test_value"}
    assert prompt.prompt_status == PromptStatus.PRODUCTION

    prompt_id = prompt.prompt_id
    response = client.get(f"/{prompt_id}", headers=headers)
    assert response.status_code == 200
    prompt = Prompt.model_validate(response.json())
    assert prompt.prompt_id == prompt_id

    prompt_status = PromptStatus.DISABLED
    response = client.post(
        f"/status/{prompt_id}?status={prompt_status.value}", headers=headers
    )
    assert response.status_code == 200
    prompt = Prompt.model_validate(response.json())
    assert prompt.prompt_status == prompt_status

    response = client.get(f"/{prompt_id}", headers=headers)
    assert response.status_code == 200
    prompt = Prompt.model_validate(response.json())
    assert prompt.prompt_status == prompt_status
