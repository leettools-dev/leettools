from abc import ABC, abstractmethod
from typing import Any, Dict

from fastapi import Request

from leettools.common.logging import logger
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.user.user_store import AbstractUserStore
from leettools.settings import SystemSettings

# probably need to move this file to common

HEADER_USERNAME_FIELD = "username"
HEADER_FULL_NAME_FIELD = "full_name"
HEADER_EMAIL_FIELD = "email"
HEADER_AUTH_UUID_FIELD = "auth_uuid"
HEADER_AUTH_USERNAME_FIELD = "auth_username"
HEADER_AUTH_PROVIDER_FIELD = "auth_provider"


class AbstractAuthorizer(ABC):
    """
    Abstract class for authorizer. The authorizer is responsible for determining
    whether user can read, write, share, or unshare the knowledge bases.
    """

    def __init__(self, settings: SystemSettings, user_store: AbstractUserStore):
        self.settings = settings
        self.user_store = user_store

    @abstractmethod
    def get_admin_user(self) -> User:
        """
        Returns the admin user, which can run admin commands.
        """
        pass

    @abstractmethod
    def get_user_from_request(self, request: Request) -> User:
        """
        Get the user object from the request header.

        Args:
        - request: Request - the request object
        """
        pass

    @abstractmethod
    def get_user_from_payload(self, user_dict: Dict[str, Any]) -> User:
        """
        Get the user object from the user_dict, usually from the request header.

        Args:
        - user_dict: Dict[str, str] - the user dictionary from the request header
        """
        pass

    @abstractmethod
    def can_read_org(self, org: Org, user: User) -> bool:
        """
        Can the user read the organization?
        """
        pass

    @abstractmethod
    def can_read_kb(self, org: Org, kb: KnowledgeBase, user: User) -> bool:
        """
        Can the user read the knowledge base? Usually
        - the user is the owner of the kb
        - the kb is shared to the public
        - the user is the admin user

        Args:
        - org: Org - the organization of the knowledge base
        - kb: KnowledgeBase - the knowledge base
        - user: User - the user

        Returns:
        - bool - whether the user can read the knowledge base

        """
        pass

    @abstractmethod
    def can_write_kb(self, org: Org, kb: KnowledgeBase, user: User) -> bool:
        """
        Can the user write to the knowledge base? Usually only the owner can write
        to the knowledge base.

        Args:
        - org: Org - the organization of the knowledge base
        - kb: KnowledgeBase - the knowledge base
        - user: User - the user

        Returns:
        - bool - whether the user can write to the knowledge base
        """
        pass

    @abstractmethod
    def can_share_kb(self, org: Org, kb: KnowledgeBase, user: User) -> bool:
        """
        Can the user share the knowledge base? Usually only the owner can share.

        Args:
        - org: Org - the organization of the knowledge base
        - kb: KnowledgeBase - the knowledge base
        - user: User - the user

        Returns:
        - bool - whether the user can share the knowledge base
        """
        pass

    @abstractmethod
    def can_unshare_kb(self, org: Org, kb: KnowledgeBase, user: User) -> bool:
        """
        Can the user unshare the knowledge base? Usually only the owner can unshare.

        Args:
        - org: Org - the organization of the knowledge base
        - kb: KnowledgeBase - the knowledge base
        - user: User - the user

        Returns:
        - bool - whether the user can unshare the knowledge base
        """
        pass

    @abstractmethod
    def _reset_for_test(self) -> None:
        pass


def create_authorizer(
    settings: SystemSettings, user_store: AbstractUserStore
) -> AbstractAuthorizer:
    from leettools.common.utils import factory_util

    if settings.AUTHORIZER is not None and settings.AUTHORIZER != "":
        authorizer = settings.AUTHORIZER
    else:
        authorizer = "eds_authorizer"

    logger().info(f"Creating authorizer: {authorizer}")
    module_name = f"{__package__}._impl.{authorizer.lower()}"
    return factory_util.create_object(
        module_name,
        AbstractAuthorizer,
        settings=settings,
        user_store=user_store,
    )
