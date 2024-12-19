from abc import ABC, abstractmethod
from typing import Any, Dict

from fastapi import Request

from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User


class AbstractAuthorizer(ABC):
    """
    Abstract class for authorizer. The authorizer is responsible for determining
    whether user can read, write, share, or unshare the knowledge bases.
    """

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


HEADER_USERNAME_FIELD = "username"
