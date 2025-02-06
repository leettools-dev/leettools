from typing import Dict, List, Optional

from fastapi import BackgroundTasks, Depends, HTTPException

from leettools.common.exceptions import EntityNotFoundException, InvalidValueException
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KBCreate, KBUpdate, KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.metadata.kb_metadata_manager import create_kb_metadata_manager
from leettools.eds.metadata.schemas.kb_metadata import KBMetadata
from leettools.flow.metadata.extract_metadata_manager import (
    create_extraction_metadata_manager,
)
from leettools.flow.schemas.extract_metadata import ExtractMetadata
from leettools.svc.api_router_base import APIRouterBase


class KnowledgeBaseRouter(APIRouterBase):
    """
    Router for handling Knowledge Base API endpoints.

    This router provides endpoints for retrieving, adding, updating, and deleting
    knowledge bases for a given organization.

    Attributes:
    - org_manager (OrgManager): The organization manager instance.
    - kb_manager (KBManager): The knowledge base manager instance.
    - auth (Authorizer): The authorizer instance for authentication and authorization.

    """

    def _get_org(self, org_name: str) -> Org:
        org = self.org_manager.get_org_by_name(org_name)
        if org is None:
            raise EntityNotFoundException(entity_name=org_name, entity_type="Org")
        return org

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        settings = context.settings
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.kb_metadata_manager = create_kb_metadata_manager(context)
        self.extract_metadata_manager = create_extraction_metadata_manager(settings)

        @self.get("/owned_by_user/{org_name}", response_model=List[KnowledgeBase])
        async def list_owned_knowledgebases(
            org_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Retrieve knowledge bases in a given organization that the calling user owned.

            Args:
            - org_name (str): The name of the organization.
            - calling_user: The calling user by dependency injection.

            Returns:
            - list: A list of knowledge bases owned by the user.
            """

            org = self._get_org(org_name)
            kbs = self.kb_manager.get_all_kbs_for_org(org)
            filtered_kbs = [kb for kb in kbs if kb.is_owner(calling_user.user_uuid)]
            return filtered_kbs

        @self.get("/shared_with_user/{org_name}", response_model=List[KnowledgeBase])
        async def list_shared_knowledgebases(
            org_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Retrieve knowledge bases in a given organization that are shared with the
            calling user. Right now, we only share with the public, so this will return
            all the shared_to_public knowledge bases.

            Args:
            - org_name (str): The name of the organization.
            - calling_user: The calling user by dependency injection.

            Returns:
            - list: A list of knowledge bases shared with the user.
            """

            org = self._get_org(org_name)
            kbs = self.kb_manager.get_all_kbs_for_org(org)
            filtered_kbs = [
                kb
                for kb in kbs
                if kb.share_to_public and not kb.is_owner(calling_user.user_uuid)
            ]
            return filtered_kbs

        @self.post("/share/{org_name}/{kb_name}", response_model=KnowledgeBase)
        async def share_knowledgebase(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> KnowledgeBase:
            """
            Share a knowledge base with the public.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base to share.
            - calling_user: The calling user by dependency injection.

            Returns:
            - The updated knowledge base.

            Raises:
            - EntityNotFoundException: If the knowledge base is not found.
            """

            org = self._get_org(org_name)
            if org is None:
                raise EntityNotFoundException(entity_name=org_name, entity_type="Org")

            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            if not self.auth.can_share_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toshare this KB {kb_name}",
                )

            kb_update = KBUpdate.from_kb_in_db_base(kb)
            kb_update.share_to_public = True

            kb_updated = self.kb_manager.update_kb(org=org, kb_update=kb_update)
            return kb_updated

        @self.post("/unshare/{org_name}/{kb_name}", response_model=KnowledgeBase)
        async def unshare_knowledgebase(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> KnowledgeBase:
            """
            Unshare a knowledge base with the public.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base to share.
            - calling_user: The calling user by dependency injection.

            Returns:
            - The updated knowledge base.

            Raises:
            - EntityNotFoundException: If the knowledge base is not found.
            """

            org = self._get_org(org_name)
            if org is None:
                raise EntityNotFoundException(entity_name=org_name, entity_type="Org")

            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            if not self.auth.can_unshare_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized tounshare this KB {kb_name}",
                )

            kb_update = KBUpdate.from_kb_in_db_base(kb)
            kb_update.share_to_public = False

            kb_updated = self.kb_manager.update_kb(org=org, kb_update=kb_update)
            return kb_updated

        @self.get(
            "/docs_from_author/{org_name}/{kb_name}/{author}",
            response_model=List[Document],
        )
        async def get_docs_from_author(
            org_name: str,
            kb_name: str,
            author: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[Document]:
            """
            Retrieves a list of documents from a given author in a knowledge base.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - author (str): The author to filter documents by.
            - calling_user: The calling user by dependency injection.

            Returns:
            - list: A list of documents from the given author.
            """

            org = self._get_org(org_name)
            if org is None:
                raise EntityNotFoundException(entity_name=org_name, entity_type="Org")

            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )

            documents = self.kb_metadata_manager.get_docs_from_author(org, kb, author)
            return documents

        @self.get(
            "/docs_with_keyword/{org_name}/{kb_name}/{keyword}",
            response_model=List[Document],
        )
        async def get_docs_with_keyword(
            org_name: str,
            kb_name: str,
            keyword: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[Document]:
            """
            Retrieves a list of documents with a given keyword in a knowledge base.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - keyword (str): The keyword to filter documents by.
            - calling_user: The calling user by dependency injection.

            Returns:
            - list: A list of documents with the given keyword.

            Raises:
            - EntityNotFoundException: If the organization or knowledge base is not found.
            - HTTPException: If the user is not authorized to access the knowledge base.
            """

            org = self._get_org(org_name)
            if org is None:
                raise EntityNotFoundException(entity_name=org_name, entity_type="Org")

            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )

            documents = self.kb_metadata_manager.get_docs_with_keyword(org, kb, keyword)
            return documents

        @self.get(
            "/docs_in_domain/{org_name}/{kb_name}/{tld}", response_model=List[Document]
        )
        async def get_docs_in_domain(
            org_name: str,
            kb_name: str,
            tld: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[Document]:
            """
            Retrieves a list of documents from a given top-level domain in a knowledge base.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - tld (str): The top-level domain to filter documents by.
            - calling_user: The calling user by dependency injection.

            Returns:
            - list: A list of documents from the given top-level domain.

            Raises:
            - EntityNotFoundException: If the organization or knowledge base is not found.
            - HTTPException: If the user is not authorized to access the knowledge base.
            """

            org = self._get_org(org_name)
            if org is None:
                raise EntityNotFoundException(entity_name=org_name, entity_type="Org")

            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )

            documents = self.kb_metadata_manager.get_docs_from_domain(org, kb, tld)
            return documents

        @self.post("/metadata/{org_name}/{kb_name}")
        async def process_kb_metadata(
            org_name: str,
            kb_name: str,
            background_tasks: BackgroundTasks,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> None:
            """
            Retrieves metadata for a given knowledge base.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - calling_user: The calling user by dependency injection.

            Returns:
            - None

            Raises:
            - EntityNotFoundException: If the knowledge base is not found.
            - HTTPException: If the user is not authorized to access the knowledge base.
            """

            org = self._get_org(org_name)
            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            # permission check
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )

            background_tasks.add_task(
                self.kb_metadata_manager.process_kb_metadata, org, kb
            )
            return

        @self.get("/metadata/{org_name}/{kb_name}", response_model=Optional[KBMetadata])
        async def get_kb_metadata(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Optional[KBMetadata]:
            """
            Retrieves metadata for a given knowledge base.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - calling_user: The calling user by dependency injection.

            Returns:
            - KBMetadata: The metadata for the knowledge base.

            Raises:
            - EntityNotFoundException: If the knowledge base is not found.
            - HTTPException: If the user is not authorized to access the knowledge base.
            """

            org = self._get_org(org_name)
            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            # permission check
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )

            kb_metadata = self.kb_metadata_manager.get_kb_metadata(org, kb.kb_id)
            return kb_metadata

        @self.get(
            "/extracted_tables/{org_name}/{kb_name}",
            response_model=Dict[str, List[ExtractMetadata]],
        )
        async def get_extracted_tables(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Dict[str, List[ExtractMetadata]]:
            """
            Retrieves a list of extracted tables for a given knowledge base.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - calling_user: The calling user by dependency injection.

            Returns:
            - dict: A dictionary of extracted table information, the key is the table
                    name and the value is a list of ExtractionInfo objects.

            Raises:
            - EntityNotFoundException: If the knowledge base is not found.
            - HTTPException: If the user is not authorized to access the knowledge base.
            """

            org = self._get_org(org_name)
            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            # permission check
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )

            extracted_tables = self.extract_metadata_manager.get_extracted_db_info(
                org=org, kb=kb
            )
            return extracted_tables

        @self.get("/{org_name}", response_model=List[KnowledgeBase])
        async def list_knowledgebases(
            org_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Retrieve knowledge bases for a given organization that the calling user can
            read.

            Args:
            - org_name (str): The name of the organization.
            - calling_user: The calling user by dependency injection.

            Returns:
            - list: A list of knowledge bases filtered based on user permissions.
            """

            org = self._get_org(org_name)
            kbs = self.kb_manager.get_all_kbs_for_org(org)
            if calling_user.user_uuid == self.auth.get_admin_user().user_uuid:
                return kbs
            filtered_kbs = [
                kb
                for kb in kbs
                if self.auth.can_read_kb(org=org, kb=kb, user=calling_user)
            ]
            return filtered_kbs

        @self.get("/{org_name}/{kb_name}", response_model=KnowledgeBase)
        async def get_knowledgebase(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Retrieves a knowledge base by its organization name and knowledge base name.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - calling_user: The calling user by dependency injection.

            Returns:
            - The knowledge base object.

            Raises:
            - EntityNotFoundException: If the knowledge base is not found.
            - HTTPException: If the user is not authorized to access the knowledge base.
            """

            org = self._get_org(org_name)
            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            # permission check
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )
            return kb

        @self.post("/{org_name}", response_model=KnowledgeBase)
        async def add_knowledgebase(
            org_name: str,
            kb_create: KBCreate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Adds a knowledge base to the specified organization.

            Args:
            - org_name (str): The name of the organization.
            - kb_create (KBCreate): The knowledge base data to be created.
            - calling_user: The calling user by dependency injection.

            Returns:
            - The created knowledge base.
            """

            org = self._get_org(org_name)
            kb_create.user_uuid = calling_user.user_uuid
            kb = self.kb_manager.add_kb(org=org, kb_create=kb_create)
            return kb

        @self.put("/{org_name}/{kb_name}", response_model=KnowledgeBase)
        async def update_knowledgebase(
            org_name: str,
            kb_name: str,
            kb_update: KBUpdate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Update a knowledge base with the provided information.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base to update.
            - kb_update (KBUpdate): The updated information for the knowledge base.
            - calling_user: The calling user by dependency injection.

            Returns:
            - The updated knowledge base.

            Raises:
            - InvalidValueException: If the provided kb_name does not match the name in kb_update.
            - HTTPException: If the user is not authorized to update the knowledge base.
            - EntityNotFoundException: If the knowledge base with the provided name is not found.
            """

            if kb_update.name != kb_name:
                raise InvalidValueException(
                    name="kb_name", expected=kb_name, actual=kb_update.name
                )
            org = self._get_org(org_name)

            # permission check
            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if not self.auth.can_write_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toupdate this KB {kb_name}",
                )

            kb = self.kb_manager.update_kb(org=org, kb_update=kb_update)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_update.name, entity_type="KnowledgeBase"
                )
            return kb

        @self.delete("/{org_name}/{kb_name}")
        async def delete_knowledgebase(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Deletes a knowledge base.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - calling_user: The calling user by dependency injection.

            Returns:
                None

            Raises:
            - HTTPException: If the user is not authorized to delete the knowledge base.

            """

            org = self._get_org(org_name)

            # permission check
            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if not self.auth.can_write_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized todelete this KB {kb_name}",
                )

            self.kb_manager.delete_kb_by_name(org=org, kb_name=kb_name)
