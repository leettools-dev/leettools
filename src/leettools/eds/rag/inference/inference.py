from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

from openai.resources.chat.completions import ChatCompletion

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy_section import StrategySection


class AbstractInference(ABC):

    @abstractmethod
    def inference(
        self,
        org: Org,
        kb: KnowledgeBase,
        query: str,
        query_metadata: ChatQueryMetadata,
        template_vars: Dict[str, str],
    ) -> Tuple[str, ChatCompletion]:
        """
        Run the inference process to get the result and the ChatCompletion object.

        Args:
        - org: The organization object.
        - kb: The knowledge base object.
        - query: The original query.
        - query_metadata: The query metadata.
        - template_vars: The template variables that can be used in the templates.

        Returns:
        - The result string.
        - The ChatCompletion object.
        """
        pass


def get_inference_by_strategy(
    context: Context,
    user: User,
    inference_section: StrategySection,
    display_logger: Optional[EventLogger] = None,
) -> AbstractInference:
    """
    Get the intention getter based on the strategy section.
    """
    strategy_name = inference_section.strategy_name
    if strategy_name.lower() == "default" or strategy_name.lower() == "true":
        from leettools.eds.rag.inference._impl.inference_dynamic import InferenceDynamic

        return InferenceDynamic(
            context=context,
            user=user,
            inference_section=inference_section,
            display_logger=display_logger,
        )
    else:
        raise exceptions.UnexpectedCaseException(
            f"Unknown query inference strategy: {strategy_name}"
        )
