from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union

from .file_object import FileObject, ExternalFileObject, EmojiObject
from .parent import AnyParent
from .rich_text import RichTextObject
from .user import NotionUser


#############################
# Define Database Properties
#############################
CHECKBOX_PROPERTY_TYPE = "checkbox"
DATE_PROPERTY_TYPE = "date"
EMAIL_PROPERTY_TYPE = "email"
ID_PROPERTY_TYPE = "unique_id"
FORMULA_PROPERTY_TYPE = "formula"
MULTI_SELECT_PROPERTY_TYPE = "multi_select"
NUMBER_PROPERTY_TYPE = "number"
PHONE_PROPERTY_TYPE = "phone_number"
RICH_TEXT_PROPERTY_TYPE = "rich_text"
SELECT_PROPERTY_TYPE = "select"
STATUS_PROPERTY_TYPE = "status"
TITLE_PROPERTY_TYPE = "title"
URL_PROPERTY_TYPE = "url"


#############################
# Define Database Query Result
#############################


class Option(BaseModel):
    color: str
    id: str
    name: str


CheckboxResult = bool


class DateResult(BaseModel):
    start: Optional[str]
    end: Optional[str]
    time_zone: Optional[str]


EmailResult = str
FormulaResult = str


class IDResult(BaseModel):
    number: int
    prefix: str


class MultiSelectResult(BaseModel):
    options: List[Option]


class NumberResult(BaseModel):
    value: str


PhoneResult = str
RichTextResult = List[RichTextObject]
SelectResult = Option
StatusResult = Option
TitleResult = List[RichTextObject]
URLResult = str


# Unsupported Result Types are
# - PeopleResult
# - RelationshipResult
# - FormulaResult (Partially implemented)
# - RollupResult
# - CreatedTimeResult
# - CreatedByResult
# - LastEditedTimeResult
# - LastEditedByResult
# - ButtonResult
class UnsupportedResult(BaseModel):
    type: str


PROPERTIES_FIELD = "properties"


AnyResult = Union[
    CheckboxResult,
    DateResult,
    EmailResult,
    FormulaResult,
    IDResult,
    MultiSelectResult,
    NumberResult,
    PhoneResult,
    RichTextResult,
    SelectResult,
    StatusResult,
    TitleResult,
    URLResult,
    UnsupportedResult,
]


#############################
# Define Database
#############################
class Cover(BaseModel):
    type: str
    external: ExternalFileObject


EmojiIcon = EmojiObject


class ExternalIcon(BaseModel):
    type: str = "external"
    external: ExternalFileObject


class FileIcon(BaseModel):
    type: str = "file"
    file: FileObject


class Database(BaseModel):
    object: str = "database"
    id: str
    created_time: str
    created_by: NotionUser
    last_edited_time: str
    last_edited_by: NotionUser
    title: Optional[List[RichTextObject]]
    description: Optional[List[RichTextObject]]
    icon: Optional[Union[EmojiIcon, ExternalIcon, FileIcon]]
    cover: Optional[Cover]
    properties: Optional[Dict[str, Any]]
    parent: Optional[AnyParent]
    url: Optional[str]
    archived: Optional[bool]
    is_inline: Optional[bool]
    public_url: Optional[str]

    @classmethod
    def from_dict(cls, data: dict) -> "Database":
        return Database.model_validate(data)

    def get_columns(self) -> List[str]:
        rtn_dict = self.model_dump()
        rtn_list = []
        for key in rtn_dict[PROPERTIES_FIELD]:
            rtn_list.append(key)
        return rtn_list

    def get_description(self) -> str:
        rtn_str = ""
        if self.description is not None:
            for item in self.description:
                rtn_str += item.plain_text
        return rtn_str


#############################
# Define DatabaseQueryResult
#############################


class DatabaseQueryResult(BaseModel):
    type: str
    column: str
    result: AnyResult

    @classmethod
    def from_dict(cls, result_type: str, column: str, data: dict) -> None:
        if result_type == CHECKBOX_PROPERTY_TYPE:
            if data is None:
                data = False
            result = data
        elif result_type == DATE_PROPERTY_TYPE:
            if data is None:
                data = {"start": None, "end": None, "time_zone": None}
            result = DateResult.model_validate(data)
        elif result_type == EMAIL_PROPERTY_TYPE:
            if data is None:
                data = ""
            result = data
        # TODO: Will be fully implemented in the future
        elif result_type == FORMULA_PROPERTY_TYPE:
            if data is None:
                result = ""
            elif "string" in data:
                result = data["string"]
            else:
                result = "formula"
        elif result_type == ID_PROPERTY_TYPE:
            if data is None:
                result = IDResult(number=0, prefix="")
            else:
                result = IDResult.model_validate(data)
        elif result_type == MULTI_SELECT_PROPERTY_TYPE:
            if data is None:
                data = []
            option_list = []
            for item in data:
                option_list.append(Option.model_validate(item))
            result = MultiSelectResult(options=option_list)
        elif result_type == NUMBER_PROPERTY_TYPE:
            if data is None:
                result = NumberResult(value="")
            else:
                result = NumberResult(value=str(data))
        elif result_type == PHONE_PROPERTY_TYPE:
            if data is None:
                data = ""
            result = data
        elif result_type == RICH_TEXT_PROPERTY_TYPE:
            if data is None:
                data = []
            rtn_list = []
            for item in data:
                rtn_list.append(RichTextObject.model_validate(item))
            result = rtn_list
        elif result_type == SELECT_PROPERTY_TYPE:
            if data is None:
                data = {}
            result = Option.model_validate(data)
        elif result_type == STATUS_PROPERTY_TYPE:
            if data is None:
                data = {}
            result = StatusResult.model_validate(data)
        elif result_type == TITLE_PROPERTY_TYPE:
            if data is None:
                data = []
            rtn_list = []
            for item in data:
                rtn_list.append(RichTextObject.model_validate(item))
            result = rtn_list
        elif result_type == URL_PROPERTY_TYPE:
            if data is None:
                result = ""
            else:
                result = data
        else:
            result = UnsupportedResult(type=result_type)
        return cls(type=result_type, column=column, result=result)

    def get_value(self) -> str:
        if self.type == CHECKBOX_PROPERTY_TYPE:
            return str(self.result)
        elif self.type == DATE_PROPERTY_TYPE:
            return (
                f"start: {self.result.start}, "
                f"end: {self.result.end}, "
                f"time_zone: {self.result.time_zone}"
            )
        elif self.type == EMAIL_PROPERTY_TYPE:
            return self.result
        elif self.type == FORMULA_PROPERTY_TYPE:
            return self.result
        elif self.type == ID_PROPERTY_TYPE:
            if self.result.prefix is not None:
                return f"{self.result.prefix}-{self.result.number}"
            else:
                return str(self.result.number)
        elif self.type == MULTI_SELECT_PROPERTY_TYPE:
            rtn_text = ""
            for option in self.result.options:
                rtn_text += f"{option.name},"
            return rtn_text
        elif self.type == NUMBER_PROPERTY_TYPE:
            return self.result.value
        elif self.type == PHONE_PROPERTY_TYPE:
            return self.result
        elif self.type == RICH_TEXT_PROPERTY_TYPE:
            if len(self.result) > 0:
                return self.result[0].plain_text
            else:
                return ""
        elif self.type == SELECT_PROPERTY_TYPE:
            return self.result.name
        elif self.type == STATUS_PROPERTY_TYPE:
            return self.result.name
        elif self.type == TITLE_PROPERTY_TYPE:
            if len(self.result) > 0:
                return self.result[0].plain_text
            else:
                return ""
        elif self.type == URL_PROPERTY_TYPE:
            return self.result
        else:
            # UnsupportedResult
            return self.result.type


#############################
# Define DatabaseQueryResults
#############################
class DatabaseQueryResults(BaseModel):
    columns: List[str]
    description: str
    results: List[List[DatabaseQueryResult]]

    def to_csv(self) -> str:
        rtn_str = ""
        for column in self.columns:
            column = column.replace("\n", " ")
            rtn_str += f"{column},"
        rtn_str = rtn_str[:-1]
        rtn_str += "\n"
        for row in self.results:
            for item in row:
                item_value = item.get_value().replace(",", "").replace("\n", " ")
                rtn_str += f"{item_value},"
            rtn_str = rtn_str[:-1]
            rtn_str += "\n"
        return f"{rtn_str}\n"

    def to_text(self) -> str:
        rtn_str = self.description + "\n"
        for column in self.columns:
            rtn_str += f"|{column}"
        rtn_str += "|\n"
        for column in self.columns:
            rtn_str += "|---"
        rtn_str += "|\n"
        for row in self.results:
            for item in row:
                rtn_str += f"|{item.get_value()}"
            rtn_str += "|\n"
        return f"{rtn_str}\n"
