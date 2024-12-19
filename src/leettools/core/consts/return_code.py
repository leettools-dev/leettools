from enum import Enum


class ReturnCode(int, Enum):
    SUCCESS = 0
    FAILURE = 1
    FAILURE_RETRY = 2
    FAILURE_ABORT = 3
