import threading
from dataclasses import dataclass
from typing import Dict, Optional

from leettools.common.logging.event_logger import EventLogger, logger
from leettools.common.singleton_meta import SingletonMeta


@dataclass
class ModelInfo:
    provider: str
    model_name: str
    context_size: int
    support_pydantic_response: bool
    support_json_response: bool
    token_map: Dict[str, Dict[str, Dict[str, Optional[float]]]]


class SingletonMetaModelInfo(SingletonMeta):
    _lock: threading.Lock = threading.Lock()


class ModelInfoManager(metaclass=SingletonMetaModelInfo):
    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._load_config()

    def _load_config(self):
        """Load model configurations from config file"""
        # TODO: Load from actual config file
        # For now using hardcoded values
        self._context_size_map = {
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-0125": 16385,
            "gpt-4": 8192,
            "gpt-4-0613": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-4-1106-preview": 128000,
            "gpt-4o": 128000,
            "gpt-4o-2024-05-13": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4o-mini-2024-07-18": 128000,
            "o1-mini": 128000,
            "deepseek-chat": 65536,
            "deepseek-reasoner": 65536,
            "llama3-8b-8192": 8192,
            "llama3-70b-8192": 8192,
            "llama3.2": 131072,
            "mixtral-8x7b-32768": 32768,
            "gemma-7b-it": 8192,
            "deepseek-v3": 65536,
            "DeepSeek-R1-Distill-Llama-70B": 65536,
        }

        self._pydantic_response_models = {"gpt-", "o1", "gemini-"}

        self._json_response_models = {
            "gpt-",
            "o1",
            "gemini-",
            "llama3.2",
            "deepseek",
        }

        self._token_map = {
            "default": {
                "inference": {
                    "input": 50,
                    "output": 150,
                    "batch_input": 25,
                    "batch_output": 75,
                },
                "embed": {
                    "input": 2,
                    "output": None,
                    "batch_input": 1,
                    "batch_output": None,
                },
            },
            "localhost": {
                "default": {
                    "input": 0,
                    "output": 0,
                    "batch_input": 0,
                    "batch_output": 0,
                },
            },
            "openai": {
                "default": {
                    "input": 15,
                    "output": 60,
                    "batch_input": 7.5,
                    "batch_output": 30,
                },
                "gpt-4o-mini": {
                    "input": 15,
                    "output": 60,
                    "batch_input": 7.5,
                    "batch_output": 30,
                },
                "gpt-4o": {
                    "input": 500,
                    "output": 1500,
                    "batch_input": 250,
                    "batch_output": 750,
                },
                "gpt-4o-2024-05-13": {
                    "input": 500,
                    "output": 1500,
                    "batch_input": 250,
                    "batch_output": 750,
                },
                "gpt-3.5-turbo": {
                    "input": 50,
                    "output": 150,
                    "batch_input": 25,
                    "batch_output": 75,
                },
                "text-embedding-3-small": {
                    "input": 2,
                    "output": None,
                    "batch_input": 1,
                    "batch_output": None,
                },
                "text-embedding-3-large": {
                    "input": 13,
                    "output": None,
                    "batch_input": 7,
                    "batch_output": None,
                },
            },
            "claude": {
                "claude-3-5-sonnet": {
                    "input": 300,
                    "output": 1500,
                    "batch_input": None,
                    "batch_output": None,
                },
                "claude-3-5-opus": {
                    "input": 1500,
                    "output": 7500,
                    "batch_input": None,
                    "batch_output": None,
                },
                "claude-3-5-haiku": {
                    "input": 25,
                    "output": 125,
                    "batch_input": None,
                    "batch_output": None,
                },
            },
            "aliyuncs": {
                "qwen-plus": {
                    "input": 50,
                    "output": 150,
                    "batch_input": None,
                    "batch_output": None,
                },
                "text-embedding-v1": {
                    "input": 13,
                    "output": None,
                    "batch_input": 1,
                    "batch_output": None,
                },
                "text-embedding-v2": {
                    "input": 13,
                    "output": None,
                    "batch_input": 7,
                    "batch_output": None,
                },
            },
            "deepseek": {
                "deepseek-v3": {
                    "input": 14,
                    "output": 28,
                    "batch_input": 14,
                    "batch_output": 28,
                },
            },
            "leettools": {
                "default": {
                    "input": 15,
                    "output": 60,
                    "batch_input": 7.5,
                    "batch_output": 30,
                }
            },
            "fireworks": {
                "default": {
                    "input": 15,
                    "output": 60,
                    "batch_input": None,
                    "batch_output": None,
                }
            },
        }

    def get_context_size(
        self,
        model_name: str,
        provider: Optional[str] = None,
        display_logger: Optional[EventLogger] = None,
    ) -> int:
        """
        Get the context size for the model.
        """
        if display_logger is None:
            display_logger = logger()

        if provider is not None:
            raise ValueError("Provider is not supported yet")

        if model_name not in self._context_size_map:
            from leettools.context_manager import ContextManager

            context = ContextManager().get_context()
            context_limit = context.settings.DEFAULT_CONTEXT_LIMIT
            display_logger.info(
                f"Model is not in the context size map: {model_name}. "
                f"Using default context size {context_limit}."
            )
            return context_limit

        return self._context_size_map.get(model_name)  # Default context size

    def support_pydantic_response(
        self, model_name: str, provider: Optional[str] = None
    ) -> bool:
        """
        Check if the model supports Pydantic response.
        """
        if provider is not None:
            raise ValueError("Provider is not supported yet")

        return any(
            model_name.startswith(prefix) for prefix in self._pydantic_response_models
        )

    def support_json_response(
        self, model_name: str, provider: Optional[str] = None
    ) -> bool:
        """
        Check if the model supports JSON response.
        """
        if provider is not None:
            raise ValueError("Provider is not supported yet")

        return any(
            model_name.startswith(prefix) for prefix in self._json_response_models
        )

    def get_token_map(self) -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
        """
        Get the token map for all the supported models.
        """
        return self._token_map

    def no_system_prompt(self, model_name: str) -> bool:
        """
        Check if the model is a no system prompt model.
        """
        return model_name.startswith("o1")

    def use_max_completion_tokens(self, model_name: str) -> bool:
        """
        Check if the model uses max completion tokens.
        """
        return model_name.startswith("o1") or model_name.startswith("gpt-")
