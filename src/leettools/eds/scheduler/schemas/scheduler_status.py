from enum import Enum


class SchedulerStatus(str, Enum):
    PAUSED = "paused"
    RUNNING = "running"
    STOPPED = "stopped"
