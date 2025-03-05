import os
import traceback
from typing import Optional

import click

from leettools.common.exceptions import UnexpectedCaseException
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils.template_eval import render_template
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_display_settings import (
    StrategySectionName,
)
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.eds.api_caller.api_caller_base import APICallerBase
from leettools.eds.rag.intention.intention_getter import (
    DEFAULT_INTENTION,
    AbstractIntentionGetter,
)

_script_dir = os.path.dirname(os.path.abspath(__file__))


class IntentionGetterDynamic(AbstractIntentionGetter, APICallerBase):
    def __init__(
        self,
        context: Context,
        user: User,
        intention_section: StrategySection,
        event_logger: Optional[EventLogger] = None,
    ) -> None:

        self.setup_with_strategy(
            context, user, intention_section, _script_dir, event_logger
        )

        self.intention_list = self.strategy_section.intention_list
        if self.intention_list is None or self.intention_list == []:
            raise UnexpectedCaseException("No intention list provided for intention.")

    def get_intention(self, question: str) -> ChatQueryMetadata:
        """
        Get the intention of the question.
        """
        self.setup_default_prompts()

        user_prompt = render_template(
            self.user_prompt_template,
            {"question": question, "intention_list": self.intention_list},
        )
        self.display_logger.noop(
            f"final user_prompt for intention: {user_prompt}", noop_lvl=2
        )

        # right now we do not have any variables in the system prompt
        system_prompt = render_template(self.system_prompt_template, {})
        self.display_logger.noop(
            f"final system_prompt for intention: {system_prompt}", noop_lvl=2
        )

        response_str = None
        try:
            response_str, _ = self.run_inference_call(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            return ChatQueryMetadata.model_validate_json(response_str)
        except Exception as e:
            if response_str is not None:
                self.display_logger.error(
                    f"ModelValidating ChatQueryMetadata failed: {response_str}"
                )
            else:
                trace = traceback.format_exc()
                self.display_logger.error(f"Failed to get intention: {trace}")
            self.display_logger.info(f"Using default intention: {DEFAULT_INTENTION}")
            return ChatQueryMetadata(intention=DEFAULT_INTENTION)


@click.command()
@click.option(
    "-q",
    "--question",
    "question",
    required=True,
    help="the question to ask",
)
@click.option(
    "-s",
    "--strategy",
    "strategy_name",
    required=False,
    help="the strategy name",
)
def intention(question: str, strategy_name: Optional[str]):
    """
    Command line interface to identify the intention of a given question. Parameters are:
    - question: The question to ask.
    - strategy_name: The strategy name.
    """

    context = ContextManager().get_context()  # type: Context
    repo_manager = context.get_repo_manager()
    strategy_store = context.get_strategy_store()
    strategy = None
    if strategy_name is not None:
        strategy = strategy_store.get_active_strategy_by_name(strategy_name, user=None)
    else:
        strategy = strategy_store.get_default_strategy()

    intention_section = strategy.strategy_sections.get(StrategySectionName.INTENTION)

    user = User.get_admin_user()

    intention_getter = IntentionGetterDynamic(
        context=context, user=user, intention_section=intention_section
    )
    intention = intention_getter.get_intention(question)
    print(intention)


if __name__ == "__main__":
    intention()
