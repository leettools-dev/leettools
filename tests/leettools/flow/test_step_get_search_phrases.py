from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.common.utils.lang_utils import is_chinese, is_english
from leettools.context_manager import Context
from leettools.core.consts.flow_option import (
    FLOW_OPTION_OUTPUT_LANGUAGE,
    FLOW_OPTION_SEARCH_LANGUAGE,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import steps


def test_get_search_phrase():

    temp_setup = TempSetup()

    context = temp_setup.context

    org, kb, user = temp_setup.create_tmp_org_kb_user()

    user = temp_setup.create_tmp_user()

    try:
        _test_flow_step(context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_flow_step(context: Context, org: Org, kb: KnowledgeBase, user: User):

    query = "Web design"

    from leettools.chat import chat_utils

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org.name,
        kb_name=kb.name,
        username=user.username,
        strategy_name=None,
        flow_options={
            FLOW_OPTION_OUTPUT_LANGUAGE: "CN",
            FLOW_OPTION_SEARCH_LANGUAGE: "EN",
        },
        display_logger=None,
    )

    query_phrases = steps.StepGenSearchPhrases.run_step(exec_info=exec_info)

    assert query_phrases is not None

    logger().info(f"query_phrases: {query_phrases}")

    assert len(query_phrases) > 0
    assert is_english(query_phrases)
    assert query_phrases.startswith('"') == False
    assert query_phrases.endswith('"') == False

    # english to chinese
    query = "website design"
    from leettools.chat import chat_utils

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org.name,
        kb_name=kb.name,
        username=user.username,
        strategy_name=None,
        flow_options={
            FLOW_OPTION_OUTPUT_LANGUAGE: "EN",
            FLOW_OPTION_SEARCH_LANGUAGE: "CN",
        },
        display_logger=None,
    )

    query_phrases = steps.StepGenSearchPhrases.run_step(exec_info=exec_info)

    assert query_phrases is not None

    logger().info(f"query_phrases: {query_phrases}")

    assert len(query_phrases) > 0
    assert is_chinese(query_phrases)
    assert query_phrases.startswith('"') == False
    assert query_phrases.endswith('"') == False
