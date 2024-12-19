import os
import traceback
from typing import Optional

import click

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils.template_eval import render_template
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_display_settings import (
    StrategySectionName,
)
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.eds.api_caller.api_caller_base import APICallerBase
from leettools.eds.rag.rewrite.rewrite import (
    AbstractQueryRewriter,
    get_query_rewriter_by_strategy,
)
from leettools.eds.rag.schemas.rewrite import Rewrite

_script_dir = os.path.dirname(os.path.abspath(__file__))


class QueryRewriterDirectDynamic(AbstractQueryRewriter, APICallerBase):
    def __init__(
        self,
        context: Context,
        user: User,
        rewrite_section: StrategySection,
        event_logger: Optional[EventLogger] = None,
    ):
        self.setup_with_strategy(
            context, user, rewrite_section, _script_dir, event_logger
        )

    def rewrite(
        self, org: Org, kb: KnowledgeBase, query: str, query_metadata: ChatQueryMetadata
    ) -> Rewrite:

        self.setup_prompts_for_intention(query_metadata)

        user_prompt = render_template(self.user_prompt_template, {"question": query})
        logger().debug(f"Final user prompt for rewrite: {user_prompt}")

        system_prompt = render_template(
            self.system_prompt_template, {"question": query}
        )
        logger().debug(f"Final system prompt for rewrite: {system_prompt}")

        try:
            response_str, completion = self.run_inference_call(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            return Rewrite.model_validate_json(response_str)
        except Exception as e:
            trace = traceback.format_exc()
            self.display_logger.error(
                f"Failed to rewrite query, will use original: {trace}"
            )
            return Rewrite(rewritten_question=query)


@click.command()
@click.option(
    "-k",
    "--kb",
    "kb_name",
    required=True,
    help="the knowledge base name",
)
@click.option(
    "-q",
    "--question",
    "question",
    required=True,
    help="the question to ask",
)
@click.option(
    "-o",
    "--org",
    "org_name",
    required=False,
    help="the organization name",
)
@click.option(
    "-i",
    "--intention",
    "intention_str",
    required=False,
    help="the intention of the question",
)
@click.option(
    "-s",
    "--strategy",
    "strategy_name",
    required=False,
    help="the strategy name",
)
@click.option(
    "-m",
    "--model",
    "model_name",
    required=False,
    help="The model name, like gpt-4 or gpt-4o-mini.",
)
def rewrite(
    kb_name: str,
    question: str,
    org_name: Optional[str],
    intention_str: Optional[str],
    strategy_name: Optional[str],
    model_name: Optional[str],
):
    """
    Command line interface to rewrite the input query to a more detailed one. Parameters are:
    - question: The question to ask.
    - intention: The intention of the question.
    - strategy_name: The strategy name.
    - model_name: The name of the model to use.
    """

    if intention_str is None:
        intention_str = "default"

    context = ContextManager().get_context()  # type: Context
    repo_manager = context.get_repo_manager()

    if org_name is not None:
        org = context.get_org_manager().get_org_by_name(org_name)
    else:
        org = context.get_org_manager().get_default_org()

    kb = context.get_kb_manager().get_kb_by_name(org, kb_name)

    strategy_store = context.get_strategy_store()
    if strategy_name is not None:
        strategy = strategy_store.get_active_strategy_by_name(strategy_name)
    else:
        strategy = strategy_store.get_default_strategy()

    rewrite_section = strategy.strategy_sections.get(StrategySectionName.REWRITE)
    if model_name is not None:
        rewrite_section.api_model_name = model_name
    rewrite_section.strategy_name = "direct"

    user = User.get_admin_user()

    query_rewriter = get_query_rewriter_by_strategy(
        context=context, user=user, rewrite_section=rewrite_section
    )

    new_query = query_rewriter.rewrite(
        org=org,
        kb=kb,
        query=question,
        query_metadata=ChatQueryMetadata(intention=intention_str),
    )
    print(new_query)


if __name__ == "__main__":
    rewrite()
