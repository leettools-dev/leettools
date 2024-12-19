from pathlib import Path
from typing import Tuple

from leettools.common.logging import get_logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.logging.log_location import LogLocator


def get_logger_for_chat(chat_id: str, query_id: str) -> Tuple[str, EventLogger]:
    """
    Get the logger for the query in the chat, which writes to a file in the log dir
    determined in the LogLocator.

    Args:
    - chat_id: The chat ID.
    - query_id: The query ID.

    Returns:
    - The logger name for the chat
    - The logger for the chat
    """
    logger_name = f"query_{query_id}"
    display_logger = get_logger(logger_name)
    display_logger.set_log_detail(thread=False, code_loc=False)
    log_location = LogLocator.get_log_dir_for_query(chat_id=chat_id, query_id=query_id)

    if Path(log_location).exists():
        if display_logger.get_file_handler() is not None:
            # the logger has been created before
            return logger_name, display_logger
        # else: this case should not happen, but we will create a new file handler

    handler = display_logger.log_to_file(log_location + "/query.log")
    handler.setFormatter(EventLogger.get_simple_formatter())
    return logger_name, display_logger
