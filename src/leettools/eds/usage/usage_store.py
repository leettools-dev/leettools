from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.user.user_store import AbstractUserStore
from leettools.eds.usage.schemas.usage_api_call import (
    UsageAPICall,
    UsageAPICallCreate,
    UsageAPICallSummary,
)
from leettools.settings import SystemSettings


class AbstractUsageStore(ABC):
    @abstractmethod
    def __init__(self, settings: SystemSettings, user_store: AbstractUserStore):
        """
        Initialize the usage store.

        Args:
        -   settings: The system settings.
        -   user_store: The user store.
        """
        pass

    @abstractmethod
    def record_api_call(self, api_usage_create: UsageAPICallCreate) -> UsageAPICall:
        """
        Record an API call usage.

        Args:
        -   api_usage_create: The API call usage to record.

        Returns:
        -   The recorded API call usage.
        """
        pass

    @abstractmethod
    def get_usage_summary_by_user(
        self,
        user_uuid: str,
        start_time_in_ms: int,
        end_time_in_ms: int,
        start: Optional[int] = 0,
        limit: Optional[int] = 0,
    ) -> UsageAPICallSummary:
        """
        For the given user, get API call usage whose end time is within the given time
        range.

        Args:
        -   user_uuid: The user UUID.
        -   start_time_in_ms: The start time in milliseconds, exclusive.
        -   end_time_in_ms: The end time in milliseconds, inclusive.
        -   start: The start index of the usage records to return.
        -   limit: The maximum number of usage records to return.

        Returns:
        -   A UsageAPICallSummary object.
        """
        pass

    @abstractmethod
    def get_api_usage_details_by_user(
        self,
        user_uuid: str,
        start_time_in_ms: int,
        end_time_in_ms: int,
        start: Optional[int] = 0,
        limit: Optional[int] = 0,
    ) -> List[UsageAPICall]:
        """
        For the given user, get API call usage whose end time is within the given time
        range.

        Args:
        -   user_uuid: The user UUID.
        -   start_time_in_ms: The start time in milliseconds, exclusive.
        -   end_time_in_ms: The end time in milliseconds, inclusive.
        -   start (Optional[int]): The start index of the usage records to return, default 0.
        -   limit (Optional[int]): The maximum number of usage records to return, 0 means no limit.

        Returns:
        -   A list of API call usage details.
        """
        pass

    @abstractmethod
    def get_api_usage_count_by_user(
        self,
        user_uuid: str,
        start_time_in_ms: int,
        end_time_in_ms: int,
    ) -> int:
        """
        For the given user, get API call usage count whose end time is within the given time
        range.

        Args:
        -   user_uuid: The user UUID.
        -   start_time_in_ms: The start time in milliseconds, exclusive.
        -   end_time_in_ms: The end time in milliseconds, inclusive.

        Returns:
        -   The count of records within the time range.
        """
        pass

    @abstractmethod
    def get_api_usage_detail_by_id(
        self, usage_record_id: str
    ) -> Optional[UsageAPICall]:
        """
        Get the API call usage detail by ID.

        Args:
        -   usage_record_id: The usage record ID.

        Returns:
        -   The API call usage detail. None if not found.
        """
        pass


def create_usage_store(
    settings: SystemSettings, user_store: AbstractUserStore
) -> AbstractUsageStore:
    """
    Get the usage store.

    Returns:
    The usage store.
    """

    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="usage_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractUsageStore,
        settings=settings,
        user_store=user_store,
    )
