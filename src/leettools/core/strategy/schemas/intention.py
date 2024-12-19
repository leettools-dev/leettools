from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.common.utils.obj_utils import add_fieldname_constants


class IntentionBase(BaseModel):
    intention: str
    description: Optional[str] = None
    display_name: Optional[str] = None
    examples: Optional[List[str]] = []
    is_active: Optional[bool] = True


class IntentionCreate(IntentionBase):
    pass


class IntentionUpdate(IntentionBase):
    pass


class IntentionInDBBase(IntentionBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@add_fieldname_constants
class Intention(IntentionInDBBase):
    pass


@dataclass
class BaseIntentionSchema(ABC):
    TABLE_NAME: str = "intention"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        return {
            Intention.FIELD_INTENTION: "VARCHAR",
            Intention.FIELD_DESCRIPTION: "VARCHAR",
            Intention.FIELD_DISPLAY_NAME: "VARCHAR",
            Intention.FIELD_EXAMPLES: "VARCHAR",
            Intention.FIELD_IS_ACTIVE: "BOOLEAN",
            Intention.FIELD_CREATED_AT: "TIMESTAMP",
            Intention.FIELD_UPDATED_AT: "TIMESTAMP",
        }
