from typing import Optional

import leettools.common.exceptions as exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context, ContextManager


class LogLocator:
    """
    This class is used to decide the location of the logs based on the type of the execution.

    There are two types of execution:
    * task: the execution of a task, the log should be corresponding to the task run uuid
    * server: the execution of a server, the log should be corresponding to the server name
    """

    @staticmethod
    def get_log_for_server(
        service_name: str,
        model_name: str,
        adapter_name: Optional[str],
        adapter_uuid: Optional[str],
    ) -> str:
        """
        Get the log location for the server.
        """
        context = ContextManager().get_context()  # type: Context
        server_log_root = f"{context.settings.LOG_ROOT}/servers"
        if adapter_name is None:
            return f"{server_log_root}/models/{model_name}/{service_name}"
        else:
            if adapter_uuid is None:
                raise exceptions.UnexpectedNullValueException(
                    "get_log_for_server", "adapter_uuid"
                )
            return f"{server_log_root}/adapters/{model_name}/{adapter_name}/{adapter_uuid}/{service_name}"

    @staticmethod
    def get_log_dir_for_task(task_uuid: str, job_uuid: str) -> str:
        """
        Get the log location for the task. We do not specify the log file name here because the
        task may write to different files or use log rotations. Right now the task_run.log_location
        is bound to a file, which may change in the future.
        """
        context = ContextManager().get_context()  # type: Context
        task_log_root = f"{context.settings.LOG_ROOT}/tasks"
        return f"{task_log_root}/{task_uuid}/{job_uuid}_run"

    @staticmethod
    def get_log_dir_for_query(chat_id: str, query_id: str) -> str:
        """
        Get the log location for the query.
        """
        context = ContextManager().get_context()  # type: Context
        query_log_root = f"{context.settings.LOG_ROOT}/queries"
        return f"{query_log_root}/{chat_id}/{query_id}"

    @staticmethod
    def get_display_logger(
        logger_name: str, chat_id: str, query_id: str
    ) -> EventLogger:
        from leettools.common.logging import get_logger

        display_logger = get_logger(logger_name)
        display_logger.set_log_detail(thread=False, code_loc=False)
        log_location = LogLocator.get_log_dir_for_query(
            chat_id=chat_id, query_id=query_id
        )
        handler = display_logger.log_to_file(log_location + "/query.log")
        handler.setFormatter(EventLogger.get_simple_formatter())
        return display_logger
