from leettools.cli import cli_utils
from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User


def test_cli_utils(tmp_path):

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(tmp_path, context, org, kb, user)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)
            logger().info(f"Finished test for store_types: {store_types}")


def _test_function(tmp_path, context: Context, org: Org, kb: KnowledgeBase, user: User):

    org_01, kb_01, user_01 = cli_utils.setup_org_kb_user(
        context=context, org_name=org.name, kb_name=kb.name, username=user.username
    )

    assert org_01.name == org.name
    assert kb_01.name == kb.name
    assert user_01.username == user.username

    org_02, kb_02, user_02 = cli_utils.setup_org_kb_user(
        context=context, org_name=org.name, kb_name="new_kb", username=None
    )

    assert org_02.name == org.name
    assert kb_02.name == "new_kb"
    assert user_02.username == User.ADMIN_USERNAME

    org_03, kb_03, user_03 = cli_utils.setup_org_kb_user(
        context=context, org_name=org.name, kb_name=None, username=user.username
    )

    assert org_03.name == org.name
    assert kb_03.name == context.settings.DEFAULT_KNOWLEDGEBASE_NAME
    assert user_03.username == user.username

    try:
        cli_utils.setup_org_kb_user(
            context=context, org_name=org.name, kb_name=kb.name, username="random_user"
        )
        assert False, "User does not exist in the organization."
    except Exception as e:
        pass

    try:
        cli_utils.setup_org_kb_user(
            context=context,
            org_name=org.name,
            kb_name=None,
            username=None,
            adhoc_kb=True,
        )
        assert False, "Adhoc KB creation requires a kb_name to be specified."
    except Exception as e:
        pass
