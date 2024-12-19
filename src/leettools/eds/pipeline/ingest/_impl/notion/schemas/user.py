from pydantic import BaseModel
from typing import Optional


#################################
# Definition for the NotionUser class
#################################
class NotionUser(BaseModel):
    object: str = "user"
    id: str
    type: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
