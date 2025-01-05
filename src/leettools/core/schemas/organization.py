from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.core.consts.org_status import OrgStatus

"""
See [README](./README.md) about the usage of different pydantic models.
"""


class OrgBase(BaseModel):
    name: str = Field(..., description="The name of the organization.")
    description: Optional[str] = Field(
        None, description="The description of the organization."
    )


class OrgCreate(OrgBase):
    pass


class OrgInDBBase(OrgBase):
    org_id: str = Field(..., description="The ID of the organization.")
    org_status: OrgStatus = Field(
        OrgStatus.ACTIVE, description="The status of the organization."
    )


class OrgUpdate(OrgInDBBase):
    pass


class OrgInDB(OrgInDBBase):
    created_at: Optional[datetime] = Field(
        None, description="The date the organization was created."
    )
    updated_at: Optional[datetime] = Field(
        None, description="The date the organization was updated."
    )

    @classmethod
    def from_org_create(OrgInDB, org_create: OrgCreate) -> "OrgInDB":
        ct = time_utils.current_datetime()
        org = OrgInDB(
            name=org_create.name,
            description=org_create.description,
            org_id="",  # will be replaced by a UUID when inserted into the DB
            created_at=ct,
            updated_at=ct,
        )
        assign_properties(org_create, org)
        return org


@add_fieldname_constants
class Org(OrgInDB):
    """
    Represents an organization that has a globally unique name in the syste.
    """

    TEST_ORG_PREFIX: ClassVar[str] = "test_org"

    @classmethod
    def get_org_db_name(cls, org_id: str) -> str:
        """
        Although the org name is unique, we use org_id as the DB name
        avoid DB rename and allow wider range of DB name chars.
        """
        from leettools.context_manager import Context, ContextManager

        context = ContextManager().get_context()  # type: Context
        if context.is_test:
            return f"{cls.TEST_ORG_PREFIX}_{org_id}"
        else:
            return f"org_{org_id}"

    @classmethod
    def from_org_in_db(Org, org_in_db: OrgInDB) -> "Org":
        org = Org(
            name=org_in_db.name,
            description=org_in_db.description,
            org_id=org_in_db.org_id,
            org_status=org_in_db.org_status,
            created_at=org_in_db.created_at,
            updated_at=org_in_db.updated_at,
        )
        assign_properties(org_in_db, org)
        return org


@dataclass
class BaseOrgSchema(ABC):
    """Abstract base schema for org implementations."""

    TABLE_NAME: str = "org"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        """Get base column definitions shared across implementations."""
        return {
            Org.FIELD_ORG_ID: "VARCHAR PRIMARY KEY",
            Org.FIELD_NAME: "VARCHAR",
            Org.FIELD_DESCRIPTION: "VARCHAR",
            Org.FIELD_ORG_STATUS: "VARCHAR",
            Org.FIELD_CREATED_AT: "TIMESTAMP",
            Org.FIELD_UPDATED_AT: "TIMESTAMP",
        }
