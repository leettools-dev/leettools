import os
from typing import Optional

from leettools.common import exceptions
from leettools.common.exceptions import ConfigValueException
from leettools.common.logging import logger
from leettools.common.utils.obj_utils import ENV_VAR_PREFIX
from leettools.context_manager import Context
from leettools.core.schemas.user import User
from leettools.core.schemas.user_settings import UserSettings


def _get_settings_value(
    user_settings: UserSettings, first_key: str, second_key: Optional[str]
) -> str:
    username = user_settings.username
    usi_first = user_settings.settings.get(first_key, None)
    if usi_first is not None:
        value = usi_first.value
    else:
        value = None
    if value is None or value == "":
        logger().noop(
            f"No first key {first_key} user settings of {username}.", noop_lvl=1
        )
        if second_key is not None:
            usi_second = user_settings.settings.get(second_key, None)
            if usi_second is not None:
                value = usi_second.value
            else:
                value = None
            if value is None or value == "":
                logger().noop(
                    f"No second key {second_key} user settings of {username}.",
                    noop_lvl=1,
                )
            else:
                logger().debug(
                    f"Using second key {second_key} user setting of {username}."
                )
    else:
        logger().debug(f"Using first key {first_key} user setting of {username}.")
    return value


def get_value_from_settings(
    context: Context,
    user_settings: UserSettings,
    default_env: str,
    first_key: str,
    second_key: Optional[str] = None,
    allow_empty: Optional[bool] = False,
) -> str:
    """
    Get a value from the settings in this order:

    If the context is service:
        - user's user-settings
        - admin's user-settings
        - value in the context system settings
        - environment variables

    If the context is CLI:
        - environment variables
        - value in the context system settings
        - user's user-settings
        - admin's user-settings

    args:
    - context: Context
    - user_settings: UserSettings
    - default_env: if no value is found in the settings, this environment variable
        will be checked
    - first_key: the first key to check in the settings
    - second_key: if the first key is not found, this key will be checked, e.g., we
            will use default open_ai_api_key if no embedly_api_key is found
    - allow_empty: if false, an exception will be raised if no value is found
    """
    if context.is_svc:
        return _get_value_from_settings_for_svc(
            context=context,
            user_settings=user_settings,
            default_env=default_env,
            first_key=first_key,
            second_key=second_key,
            allow_empty=allow_empty,
        )

    if context.is_cli():
        return _get_value_from_settings_for_cli(
            context=context,
            user_settings=user_settings,
            default_env=default_env,
            first_key=first_key,
            second_key=second_key,
            allow_empty=allow_empty,
        )

    raise exceptions.UnexpectedCaseException(
        f"Context name {context.name} is not a service or CLI."
    )


def _get_value_from_settings_for_svc(
    context: Context,
    user_settings: UserSettings,
    default_env: str,
    first_key: str,
    second_key: Optional[str] = None,
    allow_empty: Optional[bool] = False,
) -> str:
    value = _get_settings_value(
        user_settings=user_settings,
        first_key=first_key,
        second_key=second_key,
    )
    if value is not None and value != "":
        return value

    logger().noop(f"Checking admin settings ...", noop_lvl=1)
    admin_user = context.get_user_store().get_user_by_name(User.ADMIN_USERNAME)
    admin_user_settings = context.get_user_settings_store().get_settings_for_user(
        admin_user
    )
    value = _get_settings_value(
        user_settings=admin_user_settings,
        first_key=first_key,
        second_key=second_key,
    )
    if value is not None and value != "":
        return value

    logger().noop(f"Checking system settings variable {default_env} ...", noop_lvl=1)
    try:
        value = context.settings.__getattribute__(default_env)
        if value is not None and value != "":
            logger().debug(f"Using system settings variable {default_env}.")
            return value
    except AttributeError:
        logger().debug(f"No system settings variable {default_env}.")

    env_var_name = f"{ENV_VAR_PREFIX}{default_env.upper()}"

    value = os.environ.get(env_var_name, None)
    if value is not None and value != "":
        logger().debug(f"Using env variable {env_var_name}.")
        return value

    if not allow_empty:
        raise ConfigValueException(
            config_item=first_key,
            config_value="None",
        )
    return value


def _get_value_from_settings_for_cli(
    context: Context,
    user_settings: UserSettings,
    default_env: str,
    first_key: str,
    second_key: Optional[str] = None,
    allow_empty: Optional[bool] = False,
) -> str:

    env_var_name = f"{ENV_VAR_PREFIX}{default_env.upper()}"

    value = os.environ.get(env_var_name, None)
    if value is not None and value != "":
        logger().debug(f"Using env variable {env_var_name}.")
        return value

    logger().noop(f"Checking system settings variable {default_env} ...", noop_lvl=1)
    try:
        value = context.settings.__getattribute__(default_env)
        if value is not None and value != "":
            logger().debug(f"Using system settings variable {default_env}.")
            return value
    except AttributeError:
        logger().debug(f"No system settings variable {default_env}.")

    value = _get_settings_value(
        user_settings=user_settings,
        first_key=first_key,
        second_key=second_key,
    )
    if value is not None and value != "":
        return value

    logger().noop(f"Checking admin settings ...", noop_lvl=1)
    admin_user = context.get_user_store().get_user_by_name(User.ADMIN_USERNAME)
    admin_user_settings = context.get_user_settings_store().get_settings_for_user(
        admin_user
    )
    value = _get_settings_value(
        user_settings=admin_user_settings,
        first_key=first_key,
        second_key=second_key,
    )
    if value is not None and value != "":
        return value

    if not allow_empty:
        raise ConfigValueException(
            config_item=first_key,
            config_value="None",
        )
    return value
