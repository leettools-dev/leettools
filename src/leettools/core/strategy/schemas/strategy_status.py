from enum import Enum


class StrategyStatus(str, Enum):
    """
    The status of the strategy.
    """

    ACTIVE = "active"
    ARCHIVED = "archived"  # modified and renamed, can't be used in future queries
    DISABLED = "disabled"  # can't be used in future queries
    DELETED = "deleted"  # soft deleted
