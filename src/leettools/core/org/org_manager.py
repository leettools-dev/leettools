from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.schemas.organization import Org, OrgCreate, OrgUpdate
from leettools.settings import SystemSettings


class AbstractOrgManager(ABC):

    @abstractmethod
    def get_default_org(self) -> Org:
        """
        Get the default organization.
        """
        pass

    @abstractmethod
    def add_org(self, org_create: OrgCreate) -> Org:
        """
        Adds a new organization entry.
        """
        pass

    @abstractmethod
    def update_org(self, org_update: OrgUpdate) -> Optional[Org]:
        """
        Updates an existing organization entry.
        """
        pass

    @abstractmethod
    def list_orgs(self) -> List[Org]:
        """
        List all organization entries.
        """
        pass

    @abstractmethod
    def get_org_by_id(self, org_id: str) -> Optional[Org]:
        """
        Gets an organization entry by its ID.
        """
        pass

    @abstractmethod
    def get_org_by_name(self, org_name: str) -> Optional[Org]:
        """
        Gets an organization entry by its name.
        """
        pass

    @abstractmethod
    def delete_org_by_name(self, org_name: str) -> bool:
        """
        Delete an organization entry by its name.
        """
        pass

    @abstractmethod
    def delete_org_by_id(self, org_id: str) -> bool:
        """
        Delete an organization entry by its id.
        """
        pass


def create_org_manager(settings: SystemSettings) -> AbstractOrgManager:
    """
    Factory function for creating an organization manager.

    Should only use once in the global context.
    """
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="org_manager",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractOrgManager,
        settings=settings,
    )
