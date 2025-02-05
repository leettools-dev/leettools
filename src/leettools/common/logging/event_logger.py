import inspect
import io
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Dict, Optional, Union

thread_local = threading.local()


class EventLogger:
    """
    This is an event logger wrapper.
    """

    # todo: the value is Logger, need to figure out how to type hint
    __instances: Dict[str, "EventLogger"] = {}

    global_default_level: str = os.environ.get("EDS_LOG_LEVEL", "INFO")
    default_encoding: str = os.environ.get("EDS_LOG_ENCODING", "utf-8")

    @staticmethod
    def set_global_default_level(level: str) -> None:
        """Set the global default logging level.

        Args:
            level (logging._Level): The level to be set.
        """
        level = level.upper()
        EventLogger.global_default_level = level
        for logger in EventLogger.__instances.values():
            logger.set_level(level)

    @staticmethod
    def get_thread_local_instance() -> "EventLogger":
        if hasattr(thread_local, "logger"):
            return thread_local.logger

        thread_name = f"{threading.current_thread().name}-{threading.get_native_id()}"
        logger = EventLogger.get_instance(name=thread_name)
        thread_local.logger = logger
        return logger

    @staticmethod
    def get_instance(name: str = "events") -> "EventLogger":
        """Get the unique single logger instance based on name.

        Args:
        - name (str): The name of the logger.

        Returns:
        - EventLogger: An EventLogger object
        """
        if name in EventLogger.__instances:
            return EventLogger.__instances[name]
        else:
            logger = EventLogger(name=name)
            return logger

    @staticmethod
    def remove_instance(name: str = "events") -> None:
        """Remove the single logger instance based on name.

        Args:
        - name (str): The name of the logger.

        Returns:
        - EventLogger: An EventLogger object
        """
        # TOCHECK: should we worry about race conditions?
        if name in EventLogger.__instances:
            EventLogger.__instances.pop(name)

    @staticmethod
    def get_simple_formatter() -> logging.Formatter:
        fmt = "[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s"
        datefmt = "%d/%m/%y %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)
        return formatter

    def get_default_formatter(self) -> logging.Formatter:
        """Get the default formatter with no rich formatting.

        Returns:
        - logging.Formatter: The default formatter.
        """
        fmt = "[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s"
        datefmt = "%d/%m/%y %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)
        return formatter

    def __init__(self, name):
        if name in EventLogger.__instances:
            raise Exception(
                "Logger with the same name exists, you should use leettools.logging.get_logger"
            )
        else:
            env_log_noop_level = os.getenv("EDS_LOG_NOOP_LEVEL")
            if env_log_noop_level is not None:
                try:
                    log_noop_value = int(env_log_noop_level)
                    self.log_noop_level = log_noop_value
                except ValueError:
                    self.log_noop_level = 0
            else:
                self.log_noop_level = 0

            handler = None
            stdout_wrapper = sys.stdout
            # io.TextIOWrapper(
            #     sys.stdout.buffer, encoding="utf-8", line_buffering=True
            # )
            stderr_wrapper = sys.stderr
            # io.TextIOWrapper(
            #     sys.stderr.buffer, encoding="utf-8", line_buffering=True
            # )
            try:
                # enable utf-8 encoding for stdout and stderr
                if os.getenv(f"EDS_LOGGING_ENABLE_RICH"):
                    from rich.logging import Console, RichHandler

                    formatter = logging.Formatter("%(message)s")
                    handler = RichHandler(
                        show_path=False,
                        markup=True,
                        show_level=True,
                        console=Console(width=250),  # the width of each line
                        rich_tracebacks=True,
                    )
                    handler.setFormatter(formatter)
                else:
                    if os.getenv("EDS_LOGGING_TO_STDERR"):
                        handler = logging.StreamHandler(stream=stderr_wrapper)
                    else:
                        handler = logging.StreamHandler(stream=stdout_wrapper)
                    handler.setFormatter(self.get_default_formatter())
            except Exception as e:
                if os.getenv("EDS_LOGGING_TO_STDERR"):
                    handler = logging.StreamHandler(stream=stderr_wrapper)
                else:
                    handler = logging.StreamHandler(stream=stdout_wrapper)
                handler.setFormatter(self.get_default_formatter())

            self._name = name
            self._logger = logging.getLogger(name)
            self._detail_thread = True
            self._detail_code_loc = True
            self._pid = os.getpid()
            self._tid = threading.get_native_id()
            self._default_handler = handler
            self.set_level(EventLogger.global_default_level)
            if handler is not None:
                self._logger.addHandler(handler)
            self._default_handler = handler
            self._logger.propagate = False
            self._file_handler = None

            EventLogger.__instances[name] = self

    @staticmethod
    def __get_call_info():
        stack = inspect.stack()

        # stack[1] gives previous function ('info' in our case)
        # stack[2] gives before previous function and so on

        fn = stack[3][1]
        fn = fn.split("/")[-1]
        ln = stack[3][2]
        func = stack[3][3]

        return fn, ln, func

    @staticmethod
    def _check_valid_logging_level(level: str):
        assert level in [
            "INFO",
            "DEBUG",
            "WARNING",
            "ERROR",
        ], "found invalid logging level"

    def set_level(self, level: str) -> None:
        """Set the logging level

        Args:
            level (Union[int, str]): Can only be INFO, DEBUG, WARNING and ERROR.
        """
        level = level.upper()
        self._check_valid_logging_level(level)

        self.level = level
        self._logger.setLevel(getattr(logging, level))

    def get_level(self) -> str:
        """Get the logging level"""
        return self.level

    def set_log_detail(
        self,
        thread: Optional[bool] = True,
        code_loc: Optional[bool] = True,
    ) -> None:
        self._detail_thread = thread
        self._detail_code_loc = code_loc

    def log_to_file(
        self, file: Union[str, Path], level: Optional[str] = None, mode: str = "a"
    ) -> logging.FileHandler:
        """Save the logs to a file

        Args:
            file (A string or pathlib.Path object): The file to save the log.
            level (str): Can only be INFO, DEBUG, WARNING and ERROR. If None, use current logger level.
            mode (str): The mode to write log into the file.
        """
        assert isinstance(
            file, (str, Path)
        ), f"expected argument path to be type str or Path, but got {type(file)}"
        if isinstance(file, str):
            file = Path(file)
        return self.log_to_dir(file.parent, level, mode, file.name)

    def log_to_dir(
        self,
        dir: Union[str, Path],
        level: Optional[str] = None,
        mode: str = "a",
        filename: str = "events.log",
    ) -> logging.FileHandler:
        """Save the logs to a dir

        Args:
        - dir (A string or pathlib.Path object): The directory to save the log.
        - mode (str): The mode to write log into the file.
        - level (str): Can only be INFO, DEBUG, WARNING and ERROR. If None, use current logger level.
        - filename (str): a log filename, default is 'events.log'.
        """
        assert isinstance(
            dir, (str, Path)
        ), f"expected argument path to be type str or Path, but got {type(dir)}"
        if level is None:
            log_level = self.level
        else:
            log_level = level.upper()

        self._check_valid_logging_level(log_level)

        if isinstance(dir, str):
            dir = Path(dir)

        # create log directory
        dir.mkdir(parents=True, exist_ok=True)
        log_file = dir.joinpath(filename)

        # add file handler
        file_handler = logging.FileHandler(
            filename=log_file, mode=mode, encoding=self.default_encoding
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(self.get_default_formatter())
        self._logger.addHandler(file_handler)
        self._file_handler = file_handler
        return file_handler

    def get_default_handler(self) -> Optional[logging.Handler]:
        """Get the default handler of the logger.

        Returns:
        - RichHandler: The default handler of the logger.
        """
        return self._default_handler

    def remove_default_handler(self) -> None:
        if self._default_handler is not None:
            self._logger.removeHandler(self._default_handler)
            self._default_handler = None
        else:
            raise RuntimeError(
                "Trying to remove default handler while none is attached to the logger."
            )

    def get_file_handler(self) -> Optional[logging.FileHandler]:
        """Get the file handler of the logger.

        Returns:
            logging.FileHandler: The file handler of the logger.
        """
        return self._file_handler

    def remove_file_handler(self) -> None:
        try:
            if self._file_handler is not None:
                self._logger.removeHandler(self._file_handler)
                self._file_handler = None
            else:
                self._logger.warning(
                    "Trying to remove file handler while none is attached to the logger."
                )
        except Exception as e:
            self._logger.warning(f"Failed to remove file handler: {e}")

    def _log(self, level, message: str) -> None:
        getattr(self._logger, level)(message)

    def _get_full_massage(self, message: str) -> str:
        code_location = ""
        if self._detail_code_loc:
            code_location = " ({}:{} {})".format(*self.__get_call_info())
        thread_info = ""
        if self._detail_thread:
            thread_info = f"[{self._pid}-{self._tid}] "
        return f"{thread_info}{message}{code_location}"

    def info(self, message: str) -> None:
        """Log an info message.

        Args:
            message (str): The message to be logged.
        """
        self._log("info", self._get_full_massage(message))

    def warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message (str): The message to be logged.
        """
        self._log("warning", self._get_full_massage(message))

    def debug(self, message: str) -> None:
        """Log a debug message.

        Args:
            message (str): The message to be logged.
        """
        self._log("debug", self._get_full_massage(message))

    def error(self, message: str) -> None:
        """Log an error message.

        Args:
            message (str): The message to be logged.
        """
        self._log("error", self._get_full_massage(message))

    def noop(self, message: str, noop_lvl: Optional[int] = 1) -> None:
        """No-op, for place holders and temporary logging.

        Args:
        - message (str): The message to be logged.
        - noop_lvl (int): The level of the no-op, default is 1. The higher the level,
            more verbose the message. The default noop level is 0 so all noop messages
            are ignored.
        """

        if noop_lvl <= self.log_noop_level:
            self._log("debug", self._get_full_massage(message))
        return


logger = EventLogger.get_thread_local_instance
