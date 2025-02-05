import os
from typing import Optional, Tuple, Union

from openai import OpenAI
from openai.resources.chat.completions import ChatCompletion
from pydantic import BaseModel

from leettools.common.exceptions import UnexpectedCaseException
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils.file_utils import read_template_file
from leettools.context_manager import Context
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName
from leettools.eds.api_caller import api_utils
from leettools.eds.api_caller.rerank_client import AbstractRerankClient
from leettools.eds.rag.intention.intention_getter import DEFAULT_INTENTION


class APICallerBase:
    """
    The utility class for strategy sections that need API calling and setup: intention,
    rewrite, rerank, inferencees, and etc. It is basically the config and execution
    functions of an LLM-API-calling agent.

    This class should be used as an 'aspect' function class to run a specific strategy
    section and should not be used directly.
    """

    def setup_with_strategy(
        self,
        context: Context,
        user: User,
        strategy_section: StrategySection,
        script_dir: str,
        display_logger: Optional[EventLogger] = None,
    ):
        """
        Setup the LLM API caller for the strategy section.

        Args:
        -   context: The context object.
        -   user: The user object.
        -   strategy_section: The strategy section object.
        -   script_dir: The directory containing the script and prompts.
        -   display_logger: The event logger object.
        """

        from openai import OpenAI

        self.context = context
        self.user = user
        self.settings = context.settings
        self.script_dir = script_dir

        self.repo_manager = context.get_repo_manager()
        self.prompt_store = context.get_prompt_store()
        self.strategy_store = context.get_strategy_store()
        self.user_store = context.get_user_store()
        self.user_settings_store = context.get_user_settings_store()
        self.usage_store = context.get_usage_store()
        self.strategy_section = strategy_section

        if display_logger is None:
            self.display_logger = logger()
        else:
            self.display_logger = display_logger

        api_provider_username = self.strategy_section.api_provider_username
        if api_provider_username is None:
            api_provider_username = self.user.username
            api_provider_user = self.user
        else:
            api_provider_user = self.user_store.get_user_by_name(api_provider_username)

        api_provider_config_name = self.strategy_section.api_provider_config_name
        self.model_name = self.strategy_section.api_model_name
        self.model_options = self.strategy_section.api_model_options
        self.api_client: Union[OpenAI, AbstractRerankClient] = None

        if (
            strategy_section.section_name == StrategySectionName.INTENTION
            or strategy_section.section_name == StrategySectionName.REWRITE
            or strategy_section.section_name == StrategySectionName.INFERENCE
        ):
            if api_provider_config_name is None:
                self.api_provider_config = (
                    api_utils.get_default_inference_api_provider_config(
                        self.context, self.user
                    )
                )
            else:
                self.api_provider_config = (
                    self.user_settings_store.get_api_provider_config_by_name(
                        user=api_provider_user,
                        api_provider_name=api_provider_config_name,
                    )
                )
            self.api_client = api_utils.get_openai_client_for_user(
                context=context,
                user=self.user,
                api_provider_config=self.api_provider_config,
            )
            if self.model_name is None:
                self.model_name = api_utils.get_default_inference_model_for_user(
                    context, self.user
                )
                self.display_logger.debug(
                    f"Using default model {self.model_name} for {strategy_section.section_name}."
                )
            else:
                self.display_logger.debug(
                    f"Using strategy-specified model {self.model_name} for {strategy_section.section_name}."
                )
        elif strategy_section.section_name == StrategySectionName.RERANK:
            if api_provider_config_name is None:
                self.api_provider_config = (
                    api_utils.get_default_rerank_api_provider_config(
                        self.context, self.user
                    )
                )
            else:
                self.api_provider_config = (
                    self.user_settings_store.get_api_provider_config_by_name(
                        user=api_provider_user,
                        api_provider_name=api_provider_config_name,
                    )
                )
            self.api_client = api_utils.get_rerank_client_for_user(
                context=context,
                user=self.user,
                api_provider_config=self.api_provider_config,
            )
            if self.model_name is None:
                self.model_name = api_utils.get_default_rerank_model_for_user(
                    context, self.user
                )
                self.display_logger.debug(
                    f"Using default model {self.model_name} for {strategy_section.section_name}."
                )
            else:
                self.display_logger.debug(
                    f"Using strategy-specified model {self.model_name} for {strategy_section.section_name}."
                )
        else:
            self.api_provider_config = None
            self.api_client = None
            self.model_name = None

    def setup_default_prompts(self) -> None:
        self.system_prompt_template = None
        self.user_prompt_template = None

        section = self.strategy_section

        if section.strategy_name is None:
            raise UnexpectedCaseException(
                f"No strategy name provided for {section.section_name}."
            )

        if (
            section.strategy_name.lower() == "default"
            or self.strategy_section.strategy_name.lower() == "true"
        ):
            if section.llm_system_prompt_id is None:
                logger().warning(
                    "No system prompt id for {section.section_name} provided."
                    "Fallback to the default system prompt."
                )
                self.system_prompt_template = None
            else:
                system_prompt = self.prompt_store.get_prompt(
                    section.llm_system_prompt_id
                )
                if system_prompt is None:
                    logger().warning(
                        f"No system prompt found for {section.section_name} with"
                        f"id {section.llm_system_prompt_id}"
                    )
                    self.system_prompt_template = None
                else:
                    self.system_prompt_template = system_prompt.prompt_template

            if section.llm_user_prompt_id is None:
                logger().warning(
                    f"No user prompt id for {section.section_name} provided."
                    "Fallback to the default user prompt."
                )
                self.user_prompt_template = None
            else:
                user_prompt = self.prompt_store.get_prompt(section.llm_user_prompt_id)
                if user_prompt is None:
                    logger().warning(
                        f"No user prompt found for intention identification with"
                        f"id {section.llm_user_prompt_id}"
                    )
                    self.user_prompt_template = None
                else:
                    self.user_prompt_template = user_prompt.prompt_template

        if self.user_prompt_template is None:
            user_prompt_template_file = (
                f"{self.script_dir}/prompts/default_user_prompt.txt"
            )
            with open(user_prompt_template_file, "r", encoding="utf-8") as file:
                self.user_prompt_template = file.read()

        if self.system_prompt_template is None:
            system_prompt_template_file = (
                f"{self.script_dir}/prompts/default_system_prompt.txt"
            )
            with open(system_prompt_template_file, "r", encoding="utf-8") as file:
                self.system_prompt_template = file.read()

    def setup_prompts_for_intention(self, query_metadata: ChatQueryMetadata):
        # TODO: we can also decide which prompts to use based on the query language
        self.system_prompt = None
        self.user_prompt = None
        self.system_prompt_template = None
        self.user_prompt_template = None

        intention_str = query_metadata.intention
        section_name = self.strategy_section.section_name

        sp_ids = self.strategy_section.llm_system_prompt_ids_by_intention
        up_ids = self.strategy_section.llm_user_prompt_ids_by_intention

        if intention_str not in sp_ids:
            self.display_logger.warning(
                f"No system prompt id for {intention_str} provided to {section_name}."
                f"Fallback to the default intention."
            )
            intention_str = DEFAULT_INTENTION

        rewrite_sp_id = sp_ids.get(intention_str, None)
        if rewrite_sp_id is None:
            logger().warning(
                f"No system prompt id for {intention_str} provided to {section_name}."
                "Fallback to the default system prompt."
            )
            self.system_prompt_template = None
        else:
            self.system_prompt = self.prompt_store.get_prompt(rewrite_sp_id)
            if self.system_prompt is None:
                logger().warning(f"No system prompt found with id {rewrite_sp_id}.")
                self.system_prompt_template = None
            else:
                self.system_prompt_template = self.system_prompt.prompt_template

        rewrite_up_id = up_ids.get(intention_str, None)
        if rewrite_up_id is None:
            logger().warning(
                f"No user prompt id for {intention_str} provided to {section_name}."
                "Fallback to the default user prompt."
            )
            self.user_prompt_template = None
        else:
            self.user_prompt = self.prompt_store.get_prompt(rewrite_up_id)
            if self.user_prompt is None:
                logger().warning(f"No user prompt found with id {rewrite_up_id}.")
                self.user_prompt_template = None
            else:
                self.user_prompt_template = self.user_prompt.prompt_template

        if self.user_prompt_template is None:
            self.user_prompt_template = self.get_user_prompt_template_for_intention(
                intention_str
            )

        if self.system_prompt_template is None:
            self.system_prompt_template = self.get_system_prompt_template_for_intention(
                intention_str
            )

    def get_user_prompt_template_for_intention(self, intention_str: str) -> str:
        """
        Get the user prompt for the intention.
        """
        if self.script_dir is None:
            raise UnexpectedCaseException("Script directory is not set.")

        user_prompt_file = f"{self.script_dir}/prompts/{intention_str}_user_prompt.txt"
        # if the user prompt for the intention is not provided, use the default
        if not os.path.exists(user_prompt_file):
            self.display_logger.warning(
                f"User prompt for {intention_str} not found. Using default."
            )
            user_prompt_file = f"{self.script_dir}/prompts/default_user_prompt.txt"
        return read_template_file(user_prompt_file)

    def get_system_prompt_template_for_intention(self, intention_str: str) -> str:
        """
        Get the system prompt for the intention.
        """
        if self.script_dir is None:
            raise UnexpectedCaseException("Script directory is not set.")

        system_prompt_file = (
            f"{self.script_dir}/prompts/{intention_str}_system_prompt.txt"
        )
        if not os.path.exists(system_prompt_file):
            self.display_logger.warning(
                f"System prompt for {intention_str} not found. Using default."
            )
            system_prompt_file = f"{self.script_dir}/prompts/default_system_prompt.txt"
        return read_template_file(system_prompt_file)

    def run_inference_call(
        self,
        system_prompt: str,
        user_prompt: str,
        need_json: Optional[bool] = True,
        call_target: Optional[str] = None,
        override_model_name: Optional[str] = None,
        override_max_token: Optional[str] = None,
        response_pydantic_model: Optional[BaseModel] = None,
    ) -> Tuple[str, ChatCompletion]:
        """
        Run the inference call for the RAG section.

        Args:
        - system_prompt: The system prompt.
        - user_prompt: The user prompt.
        - need_json: Whether the response should be in JSON format.
        - call_target: The target of the call, used in tracking.
        - override_model_name: The model name to use.
        - override_max_token: The max token to use.
        - response_pydantic_model: The response pydantic model if using an openai
            compatible API that supports pydantic output.

        Returns:
        - The response as a string and the completion object.
        """
        display_logger = self.display_logger
        if self.api_client is None:
            raise UnexpectedCaseException("API client is not set.")

        if not isinstance(self.api_client, OpenAI):
            raise UnexpectedCaseException("API client is not OpenAI.")

        if call_target is None:
            call_target = self.strategy_section.section_name

        if self.model_options is not None:
            display_logger.info(f"Model options: {self.model_options}")
            model_options = self.model_options
        else:
            model_options = {}

        if override_max_token is not None:
            model_options["max_tokens"] = override_max_token

        if override_model_name is not None:
            final_model_name = override_model_name
            display_logger.debug(
                f"Specified to use a different model {final_model_name}"
            )
        else:
            final_model_name = self.model_name
            display_logger.debug(f"Use strategy specified model {final_model_name}")

        return api_utils.run_inference_call_direct(
            context=self.context,
            user=self.user,
            api_client=self.api_client,
            api_provider_name=self.api_provider_config.api_provider,
            model_name=final_model_name,
            model_options=model_options,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            need_json=need_json,
            call_target=call_target,
            response_pydantic_model=response_pydantic_model,
            display_logger=display_logger,
        )
