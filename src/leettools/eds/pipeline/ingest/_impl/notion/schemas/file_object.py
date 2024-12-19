from pydantic import BaseModel
from abc import ABC


#################################
# Definition for the FileObject class
#################################
class FileObjectBase(BaseModel, ABC):
    pass


class EmojiObject(FileObjectBase):
    tpye: str = "emoji"
    emoji: str


class ExternalFileObject(FileObjectBase):
    url: str


class FileObject(FileObjectBase):
    url: str
    expiry_time: str
