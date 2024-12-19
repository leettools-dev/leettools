from abc import ABC
from typing import Any, Dict, Union

from pydantic import BaseModel, ConfigDict


class MentionObjectBase(BaseModel, ABC):
    pass


class DatabaseMention(MentionObjectBase):
    type: str = "database"
    database: Dict[str, Any]

    def to_text(self) -> str:
        return f"Mention Database: {self.database['title'][0]['plain_text']}"


class DateMention(MentionObjectBase):
    type: str = "date"
    date: Dict[str, Any]

    def to_text(self) -> str:
        return f"Mention Date: {self.date['start']}"


class LinkViewMention(MentionObjectBase):
    type: str = "link_to_view"
    link_to_view: Dict[str, Any]

    def to_text(self) -> str:
        return f"Mention Link to View: {self.link_to_view['url']}"


class PageMention(MentionObjectBase):
    type: str = "page"
    page: Dict[str, Any]

    def to_text(self) -> str:
        return f"Mention Page: {self.page['title'][0]['plain_text']}"


class TemplateMention(MentionObjectBase):
    type: str = "template"
    template: Dict[str, Any]

    def to_text(self) -> str:
        return f"Mention Template: {self.template['title'][0]['plain_text']}"


class UserMention(MentionObjectBase):
    type: str = "user"
    user: Dict[str, Any]

    def to_text(self) -> str:
        return f"Mention User: {self.user['name']}"


AnyMention = Union[
    DatabaseMention,
    DateMention,
    LinkViewMention,
    PageMention,
    TemplateMention,
    UserMention,
]


class MentionObject(BaseModel):
    type: str
    mention: AnyMention

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_text(self) -> str:
        return self.mention.to_text()
