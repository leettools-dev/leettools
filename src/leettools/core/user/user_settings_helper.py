import os
from typing import Optional

from leettools.common.exceptions import ConfigValueException
from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.schemas.user import User
from leettools.core.schemas.user_settings import UserSettings


def _get_settings_value(
    user_settings: UserSettings, first_key: str, second_key: Optional[str]
) -> str:
    value = user_settings.settings[first_key].value
    username = user_settings.username
    if value is None or value == "":
        logger().debug(f"No {first_key} in the settings of {username}.")
        if second_key is not None:
            value = user_settings.settings[second_key].value
            if value is None or value == "":
                logger().debug(f"No {second_key} in the settings of {username}.")
            else:
                logger().debug(f"Using {second_key} setting of {username}.")
    else:
        logger().debug(f"Using {first_key} setting of {username}.")
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
    Get a value from the user settings, admin settings, or environment variables.

    args:
        context: Context
        user_settings: UserSettings
        default_env: if no value is found in the settings, this environment variable
            will be checked
        first_key: the first key to check in the settings
        second_key: if the first key is not found, this key will be checked, e.g., we
            will use default open_ai_api_key if no embedly_api_key is found
        allow_empty: if false, an exception will be raised if no value is found
    """
    value = _get_settings_value(
        user_settings=user_settings,
        first_key=first_key,
        second_key=second_key,
    )
    if value is not None and value != "":
        return value

    logger().debug(f"Checking admin settings.")
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

    logger().debug(f"Checking system settings variable {default_env}.")
    try:
        value = context.settings.__getattribute__(default_env)
        if value is not None and value != "":
            logger().debug(f"Using system settings variable {default_env}.")
            return value
    except AttributeError:
        logger().debug(f"No system settings variable {default_env}.")

    value = os.environ.get(default_env, None)
    if value is not None and value != "":
        logger().debug(f"Using env variable {default_env}.")
        return value

    if not allow_empty:
        raise ConfigValueException(
            config_item=first_key,
            config_value="None",
        )
    return value
