from abc import ABC
from pydantic import BaseModel
from typing import Union


#################################
# Definition for the Parent class
#################################
class ParentBase(BaseModel, ABC):
    pass


class DatabaseParent(ParentBase):
    type: str = "database_id"
    ddatabase_id: str


class PageParent(ParentBase):
    type: str = "page_id"
    page_id: str


class BlockParent(ParentBase):
    type: str = "block_id"
    block_id: str


class WorkSpaceParent(ParentBase):
    type: str = "workspace"
    workspace: bool = True


AnyParent = Union[DatabaseParent, PageParent, BlockParent, WorkSpaceParent]
