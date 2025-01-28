import sys
from typing import Any, Dict, Optional, Tuple

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger, logger
from leettools.common.utils import time_utils


def value_to_bool(value: Any) -> bool:
    """
    Convert any object value to a boolean value.
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return bool(value)

    if value is None:
        return False

    value_str = str(value)

    # Normalize the string to lowercase and strip leading/trailing whitespaces
    value_str = value_str.strip().lower()

    # Define the valid boolean representations
    if value_str in ("true", "1", "t", "yes", "y"):
        return True
    elif value_str in ("false", "0", "f", "no", "n"):
        return False
    else:
        # Raise an error for invalid values
        raise exceptions.ConfigValueException(f"Invalid boolean string: {value}")


def days_limit_to_timestamps(days_limit: int) -> Tuple[int, int]:
    """
    Convert the days limit to the start and end timestamps of the date range.
    """
    if days_limit != 0:
        end_ts = time_utils.cur_timestamp_in_ms()
        start_ts = end_ts - days_limit * 24 * 60 * 60 * 1000
    else:
        end_ts = sys.maxsize
        start_ts = 0
    return start_ts, end_ts


def get_int_option_value(
    options: Dict[str, Any],
    option_name: str,
    default_value: Optional[int] = None,
    display_logger: Optional[EventLogger] = None,
) -> Optional[int]:
    """
    Get the integer value of the option from the options.

    Args:
    -   options: The options.
    -   option_name: The name of the option.
    -   default_value: The default value of the option.
    -   display_logger: The logger to display the warning message.

    Returns:
    -   The integer value of the option.
    """
    if display_logger is None:
        display_logger = logger()

    value_obj = options.get(option_name, None)
    if value_obj is None:
        value = default_value
    else:
        try:
            value = int(value_obj)
        except ValueError:
            display_logger.warning(
                f"Failed to convert the value of the option to int {option_name}: {value_obj}."
            )
            value = default_value
    return value


def get_bool_option_value(
    options: Dict[str, Any],
    option_name: str,
    default_value: Optional[bool] = None,
    display_logger: Optional[EventLogger] = None,
) -> Optional[bool]:
    """
    Get the boolean value of the option from the options.

    Args:
    -   options: The options.
    -   option_name: The name of the option.
    -   default_value: The default value of the option.
    -   display_logger: The logger to display the warning message.

    Returns:
    -   The boolean value of the option.
    """
    if display_logger is None:
        display_logger = logger()

    value_obj = options.get(option_name, None)
    if value_obj is None:
        value = default_value
    else:
        try:
            value = value_to_bool(value_obj)
        except ValueError:
            display_logger.warning(
                f"Failed to convert the value of the option to bool {option_name}: {value_obj}."
            )
            value = default_value
    return value


def get_str_option_value(
    options: Dict[str, Any],
    option_name: str,
    default_value: Optional[bool] = None,
    display_logger: Optional[EventLogger] = None,
) -> Optional[str]:
    """
    Get the boolean value of the option from the options.

    Args:
    -   options: The options.
    -   option_name: The name of the option.
    -   default_value: The default value of the option.
    -   display_logger: The logger to display the warning message.

    Returns:
    -   The string value of the option.
    """
    if display_logger is None:
        display_logger = logger()

    value_obj = options.get(option_name, None)
    if value_obj is None:
        value = default_value
    else:
        try:
            value = str(value_obj)
        except ValueError:
            display_logger.warning(
                f"Failed to convert the value of the option to str {option_name}: {value_obj}."
            )
            value = default_value
    return value
