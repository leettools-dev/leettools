from typing import Any, Dict, Optional

from leettools.chat.history_manager import get_history_manager
from leettools.chat.schemas.chat_history import CHCreate
from leettools.common.exceptions import EntityNotFoundException
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.chat_query_item import ChatQueryItem, ChatQueryItemCreate
from leettools.core.schemas.chat_query_options import ChatQueryOptions
from leettools.core.schemas.knowledgebase import KBCreate
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy import Strategy
from leettools.flow.exec_info import ExecInfo, ExecInfoBase
from leettools.flow.flow_manager import FlowManager


def setup_exec_info_base(
    context: Context,
    org_name: Optional[str] = None,
    kb_name: Optional[str] = None,
    username: Optional[str] = None,
    kb_description: Optional[str] = None,
    ad_hoc_kb: Optional[bool] = False,
    display_logger: Optional[EventLogger] = None,
) -> ExecInfoBase:
    """
    Setup org, kb, user objects.

    If org_name, kb_name, username are not provided, we will use the default org, kb,
    and admin user.

    If org_name is specified but not found, we will raise an EntityNotFoundException.

    If kb_name is specified but not found, we will create a new kb.
    If adhoc_kb is True, we will create a new adhoc kb. In this case, we will create the
    new kb with the kb_name and set it to auto_schedule=False.

    If username is specified but not found, we will raise an EntityNotFoundException.
    """

    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()
    user_store = context.get_user_store()

    if username is None:
        user = User.get_admin_user()
    else:
        user = user_store.get_user_by_name(username)
        if user is None:
            raise EntityNotFoundException(entity_name=username, entity_type="User")

    # we will report error if the org does not exist
    # usually we do not specify the org name
    if org_name is None:
        org = org_manager.get_default_org()
    else:
        org = org_manager.get_org_by_name(org_name)
    if org is None:
        raise EntityNotFoundException(entity_name=org_name, entity_type="Organization")

    if kb_name is None:
        kb_name = context.settings.DEFAULT_KNOWLEDGEBASE_NAME
    kb = kb_manager.get_kb_by_name(org, kb_name)
    # we will create the kb if it does not exist
    if kb == None:
        if kb_description is None:
            kb_description = f"Created by auto setup."
        if ad_hoc_kb:
            auto_schedule = False
        else:
            auto_schedule = True

        kb = kb_manager.add_kb(
            org,
            KBCreate(
                name=kb_name,
                description=kb_description,
                user_uuid=user.user_uuid,
                auto_schedule=auto_schedule,
                enable_contextual_retrieval=context.settings.ENABLE_CONTEXTUAL_RETRIEVAL,
            ),
        )
    return ExecInfoBase(context, org, kb, user, display_logger)


def setup_strategy(
    context: Context,
    user: User,
    strategy_name: Optional[str] = None,
) -> Strategy:
    strategy_store = context.get_strategy_store()
    if strategy_name is not None and strategy_name != "":
        strategy = strategy_store.get_active_strategy_by_name(strategy_name, user)
        if strategy is None:
            strategy = strategy_store.get_active_strategy_by_name(
                strategy_name, User.get_admin_user()
            )
    else:
        strategy = strategy_store.get_default_strategy()

    if strategy is None:
        raise EntityNotFoundException(entity_name=strategy_name, entity_type="Strategy")
    return strategy


def setup_exec_info(
    context: Context,
    query: str,
    org_name: str,
    kb_name: str,
    username: str,
    strategy_name: Optional[str] = None,
    flow_type: Optional[str] = None,
    flow_options: Optional[Dict[str, Any]] = {},
    kb_description: Optional[str] = None,
    ad_hoc_kb: Optional[bool] = False,
    display_logger: Optional[EventLogger] = None,
) -> ExecInfo:
    """
    When given the raw query inputs, this function will process the inputs
    and create the chat query item that needed for flow execution.

    All related information will be returned in the ExecInfo object.
    """
    if kb_description is None:
        kb_description = f"Created by auto setup query {query}"

    exec_info_base = setup_exec_info_base(
        context=context,
        org_name=org_name,
        kb_name=kb_name,
        username=username,
        kb_description=kb_description,
        ad_hoc_kb=ad_hoc_kb,
        display_logger=display_logger,
    )
    org = exec_info_base.org
    kb = exec_info_base.kb
    user = exec_info_base.user
    display_logger = exec_info_base.display_logger

    strategy = setup_strategy(context, user, strategy_name)

    history_manager = get_history_manager(context)

    chat_query_options = ChatQueryOptions(
        flow_options=flow_options,
    )
    flow_manager = FlowManager(context.settings)
    if flow_type == "" or flow_type is None:
        flow_type = flow_manager.get_default_flow_type()
    flow = flow_manager.get_flow_by_type(flow_type)
    ch_entry = history_manager.add_ch_entry(
        CHCreate(
            name=query,
            org_id=org.org_id,
            kb_id=kb.kb_id,
            creator_id=user.username,
            description=f"Created by CLI command for query {query}",
            article_type=flow.get_article_type(),
        )
    )

    chat_query_item_create = ChatQueryItemCreate(
        query_content=query,
        chat_id=ch_entry.chat_id,
        flow_type=flow_type,
    )

    chat_query_item: ChatQueryItem = history_manager.add_query_item_to_chat(
        username=user.username,
        chat_query_item_create=chat_query_item_create,
        chat_query_options=chat_query_options,
        strategy=strategy,
    )

    return ExecInfo(
        context=context,
        org=org,
        kb=kb,
        user=user,
        target_chat_query_item=chat_query_item,
        display_logger=display_logger,
    )
