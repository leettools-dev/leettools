from functools import wraps

import click

from leettools.common.logging.event_logger import EventLogger


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
