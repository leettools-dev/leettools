import os
from typing import Dict, Optional, Tuple

from openai.resources.chat.completions import ChatCompletion

from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils.template_eval import render_template
from leettools.context_manager import Context
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.eds.api_caller.api_caller_base import APICallerBase
from leettools.eds.rag.inference.inference import AbstractInference

_script_dir = os.path.dirname(os.path.abspath(__file__))


class InferenceDynamic(AbstractInference, APICallerBase):

    def __init__(
        self,
        context: Context,
        user: User,
        inference_section: StrategySection,
        display_logger: Optional[EventLogger] = None,
    ) -> None:
        self.setup_with_strategy(
            context, user, inference_section, _script_dir, display_logger
        )

    def inference(
        self,
        org: Org,
        kb: KnowledgeBase,
        query: str,
        query_metadata: ChatQueryMetadata,
        template_vars: Dict[str, str],
    ) -> Tuple[str, ChatCompletion]:

        # we allow different prompts for different intentions
        self.setup_prompts_for_intention(query_metadata)

        system_prompt_template = self.system_prompt_template
        user_prompt_template = self.user_prompt_template

        if self.system_prompt is not None:
            variables = self.system_prompt.prompt_variables
            for v in variables:
                if v not in template_vars:
                    self.display_logger.warning(
                        f"The variable {v} is not support in the system prompt template."
                    )
        else:
            # we are using the default template str, ignore the check
            pass

        if self.user_prompt is not None:
            variables = self.user_prompt.prompt_variables
            for v in variables:
                if v not in template_vars:
                    self.display_logger.warning(
                        f"The variable {v} is not support in the user prompt template."
                    )
        else:
            # we are using the default template str, ignore the check
            pass

        if system_prompt_template is None:
            # should be in sync with src/leettools/strategy/default/inference_sp_default.txt
            system_prompt_template = (
                "You are an expert of answering questions with clear reasoning based "
                "on given context."
            )
        final_system_prompt = render_template(
            system_prompt_template,
            template_vars,
        )

        if user_prompt_template is None:
            # should be in sync with src/leettools/strategy/default/inference_up_default.txt
            user_prompt_template = """
{{ context_presentation }}, please answer the following question 
{{ lang_instruction }}. {{ word_count_instruction }}.
{{ reference_instruction }}
If the context does not provide enough information to answer the question, please answer 
{{ out_of_context_instruction }}
{{ lang_instruction }}.

Here is the query: {{ rewritten_query }}
Here is the context:\n{{ context }}
"""
        final_user_prompt = render_template(
            user_prompt_template,
            template_vars,
        )

        self.display_logger.noop(
            f"Final inference system prompt: {final_system_prompt}", noop_lvl=1
        )
        self.display_logger.noop(
            f"Final inference user prompt: {final_user_prompt}", noop_lvl=1
        )

        return self.run_inference_call(
            system_prompt=final_system_prompt,
            user_prompt=final_user_prompt,
            need_json=False,
        )
