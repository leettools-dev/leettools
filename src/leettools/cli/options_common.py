from functools import wraps

import click

from leettools.common.logging.event_logger import EventLogger, logger
from leettools.context_manager import ContextManager


def common_options(f):
    @wraps(f)
    @click.option(
        "-l",
        "--log-level",
        "log_level",
        default="WARNING",
        type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
        help="Set the logging level",
        show_default=True,
        callback=_set_log_level,
    )
    @click.option(
        "-j",
        "--json",
        "json_output",
        is_flag=True,
        required=False,
        help="Output the full record results in JSON format.",
    )
    @click.option(
        "--indent",
        "indent",
        default=None,
        type=int,
        required=False,
        help="The number of spaces to indent the JSON output.",
    )
    @click.option(
        "-e",
        "--env",
        "env",
        default=None,
        required=False,
        help="The environment file to use, absolute path or related to package root.",
        callback=_read_from_env,
    )
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


# This function is used to set the log level for the application automatically
def _set_log_level(ctx, param, value: str) -> str:
    if value:
        EventLogger.set_global_default_level(value.upper())
    else:
        EventLogger.set_global_default_level("WARNING")
    return value


def _read_from_env(ctx, param, value: str) -> str:
    if value:
        logger().info(f"Resetting context with new environment file {value}.")
        context = ContextManager().get_context()
        context.reset(is_test=False, new_env_file=value)
    return value
