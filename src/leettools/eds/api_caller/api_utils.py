import json
import re
import traceback
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from openai.resources.chat.completions import ChatCompletion
from pydantic import BaseModel

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.models.model_info import ModelInfoManager
from leettools.common.utils import file_utils, json_utils, time_utils, url_utils
from leettools.common.utils.content_utils import normalize_newlines, truncate_str
from leettools.common.utils.dynamic_model import gen_pydantic_example
from leettools.context_manager import Context
from leettools.core.schemas.api_provider_config import (
    APIEndpointInfo,
    APIFunction,
    APIProviderConfig,
)
from leettools.core.schemas.user import User
from leettools.core.user.user_settings_helper import get_value_from_settings
from leettools.eds.api_caller.rerank_client import AbstractRerankClient
from leettools.eds.usage.schemas.usage_api_call import (
    API_CALL_ENDPOINT_COMPLETION,
    UsageAPICallCreate,
)


def run_inference_call_direct(
    context: Context,
    user: User,
    api_client: OpenAI,
    api_provider_name: str,
    model_name: str,
    model_options: Dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    need_json: Optional[bool] = True,
    call_target: Optional[str] = None,
    response_pydantic_model: Optional[BaseModel] = None,
    display_logger: Optional[EventLogger] = None,
) -> Tuple[str, ChatCompletion]:
    """
    The function to run the inference call directly.

    We should mostly use this function for inference calls. It will handle the default
    values, handle the return values, and log the usage in the usage store.

    Args:
    - context: The context object
    - user: The user object
    - api_client: The OpenAI-compatible client
    - api_provider_name: The name of the API provider
    - model_name: The name of the model
    - model_options: The options for the model, like temperature, max_tokens, etc.
    - system_prompt: The system prompt
    - user_prompt: The user prompt
    - need_json: Whether the response needs to be converted to JSON
    - call_target: The target of the call
    - response_pydantic_model: The response Pydantic model
    - display_logger: The display logger
    """

    if display_logger is None:
        display_logger = logger()

    usage_store = context.get_usage_store()
    settings = context.settings

    # handle the values of the model options, make it more fault tolerant
    temperature = model_options.get("temperature", None)
    if temperature is None:
        temperature = settings.DEFAULT_TEMPERATURE
    else:
        try:
            temperature = float(temperature)
        except ValueError as e:
            display_logger.warning(f"Error in parsing temperature {temperature}: {e}")
            temperature = settings.DEFAULT_TEMPERATURE

    if temperature < 0 or temperature > 2:
        display_logger.error(
            f"Invalid temperature {temperature} out of range [0, 2]. Using default."
        )
        temperature = settings.DEFAULT_TEMPERATURE

    max_tokens = model_options.get("max_tokens", None)
    if max_tokens is None:
        if settings.DEFAULT_MAX_TOKENS == -1:
            max_tokens = None
        else:
            max_tokens = settings.DEFAULT_MAX_TOKENS
    else:
        if max_tokens == "":
            max_tokens = None
        else:
            try:
                max_tokens = int(max_tokens)
            except ValueError as e:
                display_logger.error(f"Error in parsing max tokens {max_tokens}: {e}")
                max_tokens = None

    use_parsed = False
    if need_json:
        if response_pydantic_model is not None:
            # check if model supports parsed response
            if ModelInfoManager().support_pydantic_response(model_name):
                format_dict = {"type": "json_schema"}
                use_parsed = True
            else:
                display_logger.info(
                    f"Target model {model_name} does not support parsed response. "
                    f"Using JSON response."
                )
                format_dict = {"type": "json_object"}

                extra_instruction = (
                    "\nPlease provide a valid JSON formatted response with length limit "
                    "by the model's max_output parameter. Use double quotes instead of "
                    "single quotes for the JSON keys and values. The response output "
                    "should not be trucated and should be strictly in the following "
                    "format:\n"
                    f"{gen_pydantic_example(response_pydantic_model, show_type=True)}\n"
                )

                user_prompt = extra_instruction + user_prompt

                use_parsed = False
        else:
            format_dict = {"type": "json_object"}
    else:
        format_dict = {"type": "text"}

    info_len = 5000
    system_prompt_info = truncate_str(normalize_newlines(system_prompt), info_len)
    user_prompt_info = truncate_str(normalize_newlines(user_prompt), info_len)

    display_logger.noop(
        f"Final system prompt(first {info_len} chars): {system_prompt_info}", noop_lvl=1
    )
    display_logger.noop(
        f"Final user prompt (first {info_len} chars): {user_prompt_info}", noop_lvl=1
    )

    start_timestamp_in_ms = time_utils.cur_timestamp_in_ms()
    completion = None
    try:
        if ModelInfoManager().no_system_prompt(model_name):
            messages = [
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]
            temperature = 1.0
        else:
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]

        if use_parsed:
            if ModelInfoManager().use_max_completion_tokens(model_name):
                completion = api_client.beta.chat.completions.parse(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_tokens,
                    response_format=response_pydantic_model,
                )
            else:
                completion = api_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_pydantic_model,
                )
        else:
            if ModelInfoManager().use_max_completion_tokens(model_name):
                completion = api_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    response_format=format_dict,
                    temperature=temperature,
                    max_completion_tokens=max_tokens,
                )
            else:
                completion = api_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    response_format=format_dict,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
        display_logger.info(
            f"({completion.usage.total_tokens}) tokens used for ({call_target})."
        )
    finally:
        end_timestamp_in_ms = time_utils.cur_timestamp_in_ms()
        if completion is not None:
            success = True
            total_token_count = completion.usage.total_tokens
            input_token_count = completion.usage.prompt_tokens
            output_token_count = completion.usage.completion_tokens
        else:
            success = False
            total_token_count = 0
            input_token_count = -1
            output_token_count = -1

        usage_api_call = UsageAPICallCreate(
            user_uuid=user.user_uuid,
            api_provider=api_provider_name,
            target_model_name=model_name,
            endpoint=API_CALL_ENDPOINT_COMPLETION,
            success=success,
            total_token_count=total_token_count,
            start_timestamp_in_ms=start_timestamp_in_ms,
            end_timestamp_in_ms=end_timestamp_in_ms,
            is_batch=False,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            call_target=call_target,
            input_token_count=input_token_count,
            output_token_count=output_token_count,
        )
        usage_store.record_api_call(usage_api_call)

    if completion is None:
        raise exceptions.UnexpectedOperationFailureException(
            operation_desc=f"LLM inference completion for {call_target}",
            error="Completion is None.",
        )

    if use_parsed:
        response_str = completion.choices[0].message.parsed.model_dump_json()
    else:

        response_str = completion.choices[0].message.content
        display_logger.debug(f"Response from inference call\n: {response_str}")
        if need_json:
            # remove any ```json``` or ``` code block markers from the response

            pattern = r"\n?```json\n?|\n?```\n?"
            response_str = re.sub(pattern, "", response_str)

            # remove the leading <think></think> content at the start if present
            response_str = re.sub(
                r"^\s*<think>.*?</think>", "", response_str, flags=re.DOTALL
            )

            # {
            # "type": "json",
            # "content": "{'items': [...]}"
            # }
            # for return data like the above, retain only the items part
            try:
                result_dict = json.loads(response_str)
                if "items" in result_dict:
                    # use only the items part
                    valid_dict = {"items": result_dict["items"]}
                    response_str = json.dumps(valid_dict)
                else:
                    if "content" in result_dict:
                        if "items" in result_dict["content"]:
                            valid_dict = {"items": result_dict["content"]["items"]}
                            response_str = json.dumps(result_dict["content"])
            except Exception as e:
                # There may be cases the response is not a valid JSON
                # but the items part is valid JSON.
                # We do not handle this case for now.
                display_logger.debug(f"Error in parsing response as JSON: {e}")
                # try to use the regular expression to extract the items part
                pattern = r"\{.*?items.*?\}\s*"
                match = re.search(pattern, response_str)
                if match:
                    response_str = match.group(0)
                else:
                    display_logger.debug(f"No items found in response.")

            display_logger.debug(f"Clean up: {response_str}")

            # we are using a model that does not support parsed response
            # we need to convert the response to Pydantic model
            if response_pydantic_model is not None:
                try:
                    response_str = json_utils.ensure_json_item_list(response_str)
                    response_obj = response_pydantic_model.model_validate_json(
                        response_str
                    )
                    response_str = response_obj.model_dump_json()
                except Exception as e:
                    display_logger.error(
                        f"Error in parsing response to Pydantic model: {e}"
                    )
                    display_logger.error(f"Response: {response_str}")
                    response_str = completion.choices[0].message.content
    return response_str, completion


def get_api_function_list() -> List[str]:
    return [api_function for api_function in APIFunction]


def get_default_inference_model_for_user(context: Context, user: User) -> str:
    if user is None:
        user = User.get_admin_user()

    user_settings = context.get_user_settings_store().get_settings_for_user(user)
    model_name = get_value_from_settings(
        context=context,
        user_settings=user_settings,
        default_env="DEFAULT_INFERENCE_MODEL",
        first_key="DEFAULT_INFERENCE_MODEL",
        second_key=None,
        allow_empty=True,
    )
    if model_name is None or model_name == "":
        model_name = context.settings.DEFAULT_INFERENCE_MODEL
    return model_name


def get_default_rerank_model_for_user(context: Context, user: User) -> str:
    if user is None:
        user = User.get_admin_user()

    user_settings = context.get_user_settings_store().get_settings_for_user(user)
    model_name = get_value_from_settings(
        context=context,
        user_settings=user_settings,
        default_env="DEFAULT_RERANK_MODEL",
        first_key="DEFAULT_RERANK_MODEL",
        second_key=None,
        allow_empty=True,
    )
    if model_name is None or model_name == "":
        model_name = context.settings.DEFAULT_RERANK_MODEL
    return model_name


def get_openai_embedder_client_for_user(
    context: Context,
    user: User,
    api_provider_config: Optional[APIProviderConfig] = None,
) -> Tuple[APIProviderConfig, OpenAI]:
    if api_provider_config is None:
        api_provider_config = get_default_embed_api_provider_config(context, user)

    api_key = api_provider_config.api_key
    base_url = api_provider_config.base_url

    trace = traceback.format_stack()
    logger().info(
        f"Creating embedding client with base_url: {base_url} "
        f"and api_key: {file_utils.redact_api_key(api_key)}"
    )
    # used to track where the call is coming from
    logger().noop(f"Calling Trace: {trace}", noop_lvl=2)
    return api_provider_config, OpenAI(base_url=base_url, api_key=api_key)


def get_default_inference_api_provider_config(
    context: Context, user: Optional[User] = None
) -> APIProviderConfig:

    if user is None:
        user = User.get_admin_user()

    settings = context.settings
    user_settings = context.get_user_settings_store().get_settings_for_user(user)
    api_key = get_value_from_settings(
        context=context,
        user_settings=user_settings,
        default_env="LLM_API_KEY",
        first_key="LLM_API_KEY",
        second_key=None,
        allow_empty=True,
    )
    if api_key is None:
        logger().info("No API key found for inference. Using a dummy key.")
        api_key = "dummy-inference-api-key"

    base_url = get_value_from_settings(
        context=context,
        user_settings=user_settings,
        default_env="DEFAULT_LLM_BASE_URL",
        first_key="DEFAULT_LLM_BASE_URL",
        second_key=None,
        allow_empty=False,
    )

    tld = url_utils.get_first_level_domain_from_url(base_url)

    api_provider_config = APIProviderConfig(
        api_provider=tld,
        api_key=api_key,
        base_url=base_url,
        endpoints={
            APIFunction.INFERENCE: APIEndpointInfo(
                path="chat/completions",
                default_model=settings.DEFAULT_INFERENCE_MODEL,
                supported_models=["gpt-3.5-turbo", "gpt-4.0", "gpt-4o", "gpt-4o-mini"],
            ),
        },
    )
    return api_provider_config


def get_default_embed_api_provider_config(
    context: Context, user: Optional[User] = None
) -> APIProviderConfig:

    if user is None:
        user = User.get_admin_user()

    settings = context.settings
    user_settings = context.get_user_settings_store().get_settings_for_user(user)
    api_key = get_value_from_settings(
        context=context,
        user_settings=user_settings,
        default_env="EMBEDDING_API_KEY",
        first_key="EMBEDDING_API_KEY",
        second_key="LLM_API_KEY",
        allow_empty=True,
    )
    if api_key is None or api_key == "":
        api_key = get_value_from_settings(
            context=context,
            user_settings=user_settings,
            default_env="LLM_API_KEY",
            first_key="LLM_API_KEY",
            second_key=None,
            allow_empty=True,
        )
    if api_key is None or api_key == "":
        logger().info("No API key found for embedding. Using a dummy key.")
        api_key = "dummy-embedding-api-key"

    base_url = get_value_from_settings(
        context=context,
        user_settings=user_settings,
        default_env="DEFAULT_EMBEDDING_BASE_URL",
        first_key="DEFAULT_EMBEDDING_BASE_URL",
        second_key="DEFAULT_LLM_BASE_URL",
        allow_empty=True,
    )

    if base_url is None or base_url == "":
        base_url = get_value_from_settings(
            context=context,
            user_settings=user_settings,
            default_env="DEFAULT_LLM_BASE_URL",
            first_key="DEFAULT_LLM_BASE_URL",
            second_key=None,
            allow_empty=False,
        )
    logger().info(f"base_url: {base_url}")

    tld = url_utils.get_first_level_domain_from_url(base_url)

    return APIProviderConfig(
        api_provider=tld,
        api_key=api_key,
        base_url=base_url,
        endpoints={
            APIFunction.EMBED: APIEndpointInfo(
                path="embeddings",
                default_model=settings.DEFAULT_EMBEDDING_MODEL,
                supported_models=[settings.DEFAULT_EMBEDDING_MODEL],
            ),
        },
    )


def get_default_rerank_api_provider_config(
    context: Context, user: Optional[User] = None
) -> APIProviderConfig:

    if user is None:
        user = User.get_admin_user()

    settings = context.settings
    user_settings = context.get_user_settings_store().get_settings_for_user(user)

    api_key = get_value_from_settings(
        context=context,
        user_settings=user_settings,
        default_env="RERANK_API_KEY",
        first_key="RERANK_API_KEY",
        second_key=None,
        allow_empty=False,
    )
    base_url = get_value_from_settings(
        context=context,
        user_settings=user_settings,
        default_env="DEFAULT_RERANK_BASE_URL",
        first_key="DEFAULT_RERANK_BASE_URL",
        second_key=None,
        allow_empty=True,
    )

    if base_url is None:
        raise exceptions.ConfigValueException(
            "RERANK_BASE_URL",
            "RERANK_BASE_URL is not set. Please set RERANK_BASE_URL in the environment or user settings.",
        )

    tld = url_utils.get_first_level_domain_from_url(base_url)

    return APIProviderConfig(
        api_provider=tld,
        api_key=api_key,
        base_url=base_url,
        endpoints={
            APIFunction.RERANK: APIEndpointInfo(
                path="rerank",
                default_model=settings.DEFAULT_RERANK_MODEL,
                supported_models=[settings.DEFAULT_RERANK_MODEL],
            ),
        },
    )


def get_openai_client_for_user(
    context: Context, user: User, api_provider_config: APIProviderConfig
) -> OpenAI:

    if api_provider_config is None:
        logger().info(
            f"No API provider config provided. Checking user settings of {user.username} "
        )
        api_provider_config = get_default_inference_api_provider_config(context, user)

    api_key = api_provider_config.api_key
    base_url = api_provider_config.base_url

    trace = traceback.format_stack()
    logger().debug(
        f"Creating OpenAI-compatible client with base_url: {base_url} "
        f"and api_key: {api_key[:5]}******{api_key[-5:]}"
    )
    logger().noop(f"Calling Trace: {trace}", noop_lvl=2)
    return OpenAI(base_url=base_url, api_key=api_key)


def get_rerank_client_for_user(
    context: Context, user: User, api_provider_config: APIProviderConfig
) -> AbstractRerankClient:
    """
    Right now rerank client is only for Cohere.
    """

    if api_provider_config is None:
        api_provider_config = get_default_rerank_api_provider_config(context, user)

    api_key = api_provider_config.api_key
    base_url = api_provider_config.base_url

    import cohere

    if api_provider_config.base_url is not None:
        cohere_client = cohere.Client(api_key=api_key, base_url=base_url)
        logger().info(
            f"Creating Cohere client with API key: {api_key[:5]}******{api_key[-5:]} "
            f"and base_url {base_url}"
        )
    else:
        cohere_client = cohere.Client(api_key=api_key)
        logger().info(
            f"Creating Cohere client with API key: {api_key[:5]}******{api_key[-5:]} "
            "and default base_url"
        )
    return cohere_client
