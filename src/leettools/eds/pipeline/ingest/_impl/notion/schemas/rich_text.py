from pydantic import BaseModel
from typing import Any, Dict, Optional, Union
from .mention import MentionObject

class EquationObject(BaseModel):
    expression: str

class TextObject(BaseModel):
    content: str
    link: Optional[Dict[str, str]] = None

AnyRichText = Union[TextObject, MentionObject, EquationObject]

class Annotations(BaseModel):
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    code: bool = False
    color: Optional[str] = None

class RichTextObject(BaseModel):
    type: str = "text"
    rich_text: Optional[AnyRichText] = None
    text: Optional[Dict[str, Any]] = None
    annotations: Annotations
    plain_text: str
    href: Optional[str] = None

    def to_text(self) -> str:
        return self.plain_text
