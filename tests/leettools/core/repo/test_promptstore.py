""" Tests for the DocumentStore class. """

from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.prompt import (
    PromptCategory,
    PromptCreate,
    PromptStatus,
    PromptType,
)


def test_pomptstore():

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(context, org, kb, user)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb, user)


def _test_function(context: Context, org: Org, kb: KnowledgeBase, user: User):

    prompt_create = PromptCreate(
        prompt_template="""
        test prompt {{var1}}
        """,
        prompt_category=PromptCategory.INFERENCE,
        prompt_type=PromptType.SYSTEM,
        prompt_variables={"var1": "value1"},
    )

    promptstore = context.get_prompt_store()

    # Test create_prompt
    prompt = promptstore.create_prompt(prompt_create)
    assert prompt.prompt_id is not None
    assert prompt.prompt_template == prompt_create.prompt_template
    assert prompt.prompt_category == prompt_create.prompt_category
    assert prompt.prompt_type == prompt_create.prompt_type
    assert prompt.prompt_variables == prompt_create.prompt_variables
    assert prompt.prompt_status == PromptStatus.PRODUCTION

    logger().info(f"Created prompt with ID: {prompt.prompt_id}")

    # Test get_prompt
    prompt_id = prompt.prompt_id
    prompt_retrieved = promptstore.get_prompt(prompt_id)
    assert prompt_retrieved is not None
    assert prompt_retrieved.prompt_id == prompt_id
    assert prompt_retrieved.prompt_template == prompt_create.prompt_template
    assert prompt_retrieved.prompt_category == prompt_create.prompt_category
    assert prompt_retrieved.prompt_type == prompt_create.prompt_type
    logger().info(f"Retrieved prompt with ID: {prompt.prompt_id}")

    # Test list_prompts
    prompts = promptstore.list_prompts()
    assert len(prompts) > 0
    logger().info(f"Listed {len(prompts)} prompts")

    # Test list_prompts_by_category_and_type
    prompts = promptstore.list_prompts_by_filter(
        category=PromptCategory.INFERENCE, type=PromptType.SYSTEM, status=None
    )

    # Test set_prompt_status
    prompt_status = PromptStatus.DISABLED
    prompt_updated = promptstore.set_prompt_status(prompt_id, prompt_status)
    assert prompt_updated.prompt_status == prompt_status

    prompt_check = promptstore.get_prompt(prompt_id)
    assert prompt_check.prompt_status == prompt_status

    prompt_status = PromptStatus.PRODUCTION
    prompt_updated = promptstore.set_prompt_status(prompt_id, prompt_status)
    prompt_check = promptstore.get_prompt(prompt_id)
    assert prompt_check.prompt_status == prompt_status
