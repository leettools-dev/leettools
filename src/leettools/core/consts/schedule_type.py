from enum import Enum


class ScheduleType(str, Enum):
    MANUAL = "manual"  # manual run, no retry, no schedule
    ONCE = "once"  # run once until success or retry limit reached
    RECURRING = "recurring"  # run on a schedule
