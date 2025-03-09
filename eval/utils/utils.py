from typing import Optional

from leettools.chat import chat_utils
from leettools.chat.history_manager import get_history_manager
from leettools.cli.cli_utils import setup_org_kb_user
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context, ContextManager
from leettools.core.consts import flow_option
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.retriever_type import RetrieverType
from leettools.flow.exec_info import ExecInfo


def setup_context(kb_name: str) -> Context:
    """Setup and return the context for ingestion"""
    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_eval-{kb_name}"
    return context


def setup_exec_info(kb_name: str, context: Optional[Context] = None, 
                    logger: Optional[EventLogger] = None,
                    strategy_name: Optional[str] = None,
                    return_org_kb_user: bool = False) -> ExecInfo:
    """Setup execution info for both ingestion and query processes
    
    Args:
        kb_name: Name of the knowledge base
        context: Optional existing context. If None, creates new context
        logger: Optional logger instance
    
    Returns:
        ExecInfo: Configured execution info
    """
    if context is None:
        context = setup_context(kb_name)
    
    # Setup organization, KB and user
    org, kb, user = setup_org_kb_user(context, None, kb_name, None)
    
    exec_info = chat_utils.setup_exec_info(
        context=context,
        query="dummy",
        org_name=org.name,
        kb_name=kb_name,
        username=user.username,
        strategy_name=strategy_name,
        flow_options={
            flow_option.FLOW_OPTION_RETRIEVER_TYPE: RetrieverType.LOCAL,
        },
        display_logger=logger,
    )
    
    return (exec_info, org, kb, user) if return_org_kb_user else exec_info