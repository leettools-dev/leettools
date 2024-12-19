from .event_logger import EventLogger, logger

__all__ = ["get_logger", "remove_logger", "logger"]


def get_logger(name: str = "events") -> EventLogger:
    """Get logger instance based on name.

    Args:
        name (str): unique name of the logger

    Returns:
        :class:`leettools.logging.EventLogger`: A logger singleton instance.
    """
    return EventLogger.get_instance(name=name)


def remove_logger(name: str = "events") -> None:
    """Remove logger instance based on name.

    Args:
        name (str): unique name of the logger

    Returns:
        None
    """
    return EventLogger.remove_instance(name=name)
