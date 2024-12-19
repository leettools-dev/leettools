import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from notion_client import Client
from pydantic import BaseModel, ConfigDict

from .database import Database, DatabaseQueryResult, DatabaseQueryResults
from .file_object import EmojiObject, ExternalFileObject, FileObject
from .mention import MentionObject
from .parent import AnyParent
from .rich_text import RichTextObject
from .user import NotionUser


#################################
# Definition for the Block Object class
#################################
class BlockObjectBase(BaseModel, ABC):
    @abstractmethod
    def to_text(self) -> str:
        pass


class BookmarkBlock(BlockObjectBase):
    caption: List[RichTextObject]
    url: str

    def to_text(self) -> str:
        caption_text = " ".join([rt.to_text() for rt in self.caption])
        return f"Bookmark:{caption_text}\n{self.url}\n"


class BreadCrumbBlock(BlockObjectBase):
    def to_text(self) -> str:
        return ""


class BulletedListItemBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    color: str
    children: List["Block"] = []

    def to_text(self) -> str:
        rnt_rich_text = " ".join([f"- {rt.to_text()}" for rt in self.rich_text])
        if len(self.children) > 0:
            rtn_children = "\n".join([child.to_text() for child in self.children])
            rnt_rich_text += f"\n{rtn_children}"

        return f"{rnt_rich_text}\n"


class CalloutBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    icon: Union[EmojiObject, ExternalFileObject, FileObject]
    color: str

    def to_text(self) -> str:
        rtn_text = " ".join([rt.to_text() for rt in self.rich_text])
        return f"Callout:\n{rtn_text}\n"


class ChildDatabaseBlock(BlockObjectBase):
    title: str

    def to_text(self) -> str:
        return f"Child Database: {self.title}\n"


class ChildPageBlock(BlockObjectBase):
    title: str

    def to_text(self) -> str:
        return f"Child Page: {self.title}\n"


class CodeBlock(BlockObjectBase):
    caption: List[RichTextObject]
    rich_text: List[RichTextObject]
    language: str

    def to_text(self) -> str:
        rtn_text = " ".join([rt.to_text() for rt in self.rich_text])
        return f"Code in {self.language}:\n```{rtn_text}\n```"


class ColumnListBlock(BlockObjectBase):
    def to_text(self) -> str:
        return ""


class ColumnBlock(BlockObjectBase):
    def to_text(self) -> str:
        return ""


class DividerBlock(BlockObjectBase):
    def to_text(self) -> str:
        return ""


class EmbedBlock(BlockObjectBase):
    url: str

    def to_text(self) -> str:
        return self.url


class EquationBlock(BlockObjectBase):
    expression: str

    def to_text(self) -> str:
        return self.expression


class FileBlock(BlockObjectBase):
    caption: List[RichTextObject]
    type: str
    file: Union[ExternalFileObject, FileObject]
    name: str

    def to_text(self) -> str:
        caption_text = " ".join([rt.to_text() for rt in self.caption])
        return f"File:\nname: {self.name}\ncaption:{caption_text}\n{self.file.url}\n"


class HeadingOneBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    color: str
    is_toggleable: bool

    def to_text(self) -> str:
        rtn_rich_text = " ".join([rt.to_text() for rt in self.rich_text])
        return f"# {rtn_rich_text}\n"


class HeadingTwoBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    color: str
    is_toggleable: bool

    def to_text(self) -> str:
        rtn_rich_text = " ".join([rt.to_text() for rt in self.rich_text])
        return f"## {rtn_rich_text}\n"


class HeadingThreeBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    color: str
    is_toggleable: bool

    def to_text(self) -> str:
        rtn_rich_text = " ".join([rt.to_text() for rt in self.rich_text])
        return f"### {rtn_rich_text}\n"


class ImageBlock(BlockObjectBase):
    type: str
    file: Union[ExternalFileObject, FileObject]

    def to_text(self) -> str:
        return f"Image:\n{self.file.url}\n"


class LinkPreviewBlock(BlockObjectBase):
    url: str

    def to_text(self) -> str:
        return f"LinkPreview:\n{self.url}\n"


class MentionBlock(BlockObjectBase):
    mention: MentionObject

    def to_text(self) -> str:
        return self.mention.to_text()


class NumberedListItemBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    color: str
    children: List["Block"] = []

    def to_text(self) -> str:
        rnt_rich_text = " ".join([rt.to_text() for rt in self.rich_text])
        if len(self.children) > 0:
            rtn_children = "\n".join([child.to_text() for child in self.children])
            rnt_rich_text += f"\n{rtn_children}"

        return f"NumberedListItem:\n{rnt_rich_text}\n"


class ParagraphBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    color: str
    children: List["Block"] = []

    def to_text(self) -> str:
        rnt_rich_text = " ".join([rt.to_text() for rt in self.rich_text])
        if len(self.children) > 0:
            rtn_children = "\n".join([child.to_text() for child in self.children])
            rnt_rich_text += f"\n{rtn_children}"

        return f"{rnt_rich_text}\n"


class PDFBlock(BlockObjectBase):
    type: str
    file: Union[ExternalFileObject, FileObject]

    def to_text(self) -> str:
        return f"PDF:\n{self.file.url}\n"


class QuoteBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    color: str
    children: List["Block"] = []

    def to_text(self) -> str:
        rnt_rich_text = " ".join([rt.to_text() for rt in self.rich_text])
        if len(self.children) > 0:
            rtn_children = "\n".join([child.to_text() for child in self.children])
            rnt_rich_text += f"\n{rtn_children}"

        return f"Quote:\n{rnt_rich_text}\n"


class SyncedBlock(BlockObjectBase):
    def to_text(self) -> str:
        return ""


class TableBlock(BlockObjectBase):
    table_width: int
    has_column_header: bool
    has_row_header: bool

    def to_text(self) -> str:
        return ""


class TableRowsBlock(BlockObjectBase):
    cells: List[Optional[List[RichTextObject]]]

    def to_text(self) -> str:
        cells_text = " "
        for rt_list in self.cells:
            if len(rt_list) > 0:
                cells_text += rt_list[0].to_text()
        return f"{cells_text}\n"


class TableOfContentsBlock(BlockObjectBase):
    color: str

    def to_text(self) -> str:
        return ""


class TemplateBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    children: List["Block"] = []

    def to_text(self) -> str:
        rnt_rich_text = " ".join([rt.to_text() for rt in self.rich_text])
        if len(self.children) > 0:
            rtn_children = "\n".join([child.to_text() for child in self.children])
            rnt_rich_text += f"\n{rtn_children}"

        return f"Template:\n{rnt_rich_text}\n"


class TodoBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    checked: bool
    color: str

    def to_text(self) -> str:
        todo_text = " ".join([rt.to_text() for rt in self.cells])
        return f"TableRows:\n{todo_text}\n"


class ToggleBlock(BlockObjectBase):
    rich_text: List[RichTextObject]
    color: str
    children: List["Block"] = []

    def to_text(self) -> str:
        rnt_rich_text = " ".join([rt.to_text() for rt in self.rich_text])
        if len(self.children) > 0:
            rtn_children = "\n".join([child.to_text() for child in self.children])
            rnt_rich_text += f"\n{rtn_children}"

        return f"Toggle:\n{rnt_rich_text}\n"


class VideoBlock(BlockObjectBase):
    type: str
    file: Union[ExternalFileObject, FileObject]

    def to_text(self) -> str:
        return f"Video:\n{self.file.url}\n"


class UnsupportedBlock(BlockObjectBase):
    def to_text(self) -> str:
        return ""


# Union type for any block
AnyBlockObject = Union[
    BookmarkBlock,
    BreadCrumbBlock,
    BulletedListItemBlock,
    CalloutBlock,
    ChildDatabaseBlock,
    ChildPageBlock,
    CodeBlock,
    ColumnListBlock,
    ColumnBlock,
    DividerBlock,
    EmbedBlock,
    EquationBlock,
    FileBlock,
    HeadingOneBlock,
    HeadingTwoBlock,
    HeadingThreeBlock,
    ImageBlock,
    LinkPreviewBlock,
    MentionBlock,
    NumberedListItemBlock,
    ParagraphBlock,
    PDFBlock,
    QuoteBlock,
    SyncedBlock,
    TableBlock,
    TableRowsBlock,
    TableOfContentsBlock,
    TemplateBlock,
    TodoBlock,
    ToggleBlock,
    VideoBlock,
    UnsupportedBlock,
]


BOOKMARK_TYPE = "bookmark"
BREADCRUMB_TYPE = "breadcrumb"
BULLETED_LIST_TYPE = "bulleted_list_item"
CALL_OUT_TYPE = "callout"
CHILD_DATABASE_TYPE = "child_database"
CHILD_PAGE_TYPE = "child_page"
CODE_TYPE = "code"
COLUMN_LIST_TYPE = "column_list"
COLUMN_TYPE = "column"
DIVIDER_TYPE = "divider"
EMBED_TYPE = "embed"
EQUATION_TYPE = "equation"
FILE_TYPE = "file"
HEADING_1_TYPE = "heading_1"
HEADING_2_TYPE = "heading_2"
HEADING_3_TYPE = "heading_3"
IMAGE_TYPE = "image"
LINK_PREVIEW_TYPE = "link_preview"
MENTION_TYPE = "mention"
NUMBERED_LIST_TYPE = "numbered_list_item"
PARAGRAPH_TYPE = "paragraph"
PDF_TYPE = "pdf"
QUOTE_TYPE = "quote"
SYNCED_BLOCK_TYPE = "synced_block"
TABLE_TYPE = "table"
TABLE_OF_CONTENTS_TYPE = "table_of_contents"
TABLEROW_TYPE = "table_row"
TEMPLATE_TYPE = "template"
TODO_TYPE = "to_do"
TOGGLE_TYPE = "toggle"
VIDEO_TYPE = "video"
UNSUPPORTED_TYPE = "unsupported"


BLOCK_OBJECT_FIELD = "block_object"
TYPE_FIELD = "type"
CHILDREN_FIELD = "children"


class Block(BaseModel):

    object: str = "block"
    id: str
    parent: AnyParent
    type: str
    # When initializing, we set block_object to be None first
    # Then we will set it to the correct block object type
    block_object: Optional[AnyBlockObject] = None
    created_time: Optional[str] = None
    last_edited_time: Optional[str] = None
    last_edited_by: Optional[NotionUser] = None
    has_children: bool
    children: List["Block"] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        if data[TYPE_FIELD] == BOOKMARK_TYPE:
            block_object = BookmarkBlock.model_validate(data[BOOKMARK_TYPE])
        elif data[TYPE_FIELD] == BREADCRUMB_TYPE:
            block_object = BreadCrumbBlock.model_validate(data[BREADCRUMB_TYPE])
        elif data[TYPE_FIELD] == BULLETED_LIST_TYPE:
            block_object = BulletedListItemBlock.model_validate(
                data[BULLETED_LIST_TYPE]
            )
        elif data[TYPE_FIELD] == CALL_OUT_TYPE:
            block_object = CalloutBlock.model_validate(data[CALL_OUT_TYPE])
        elif data[TYPE_FIELD] == CHILD_DATABASE_TYPE:
            block_object = ChildDatabaseBlock.model_validate(data[CHILD_DATABASE_TYPE])
        elif data[TYPE_FIELD] == CHILD_PAGE_TYPE:
            block_object = ChildPageBlock.model_validate(data[CHILD_PAGE_TYPE])
        elif data[TYPE_FIELD] == CODE_TYPE:
            block_object = CodeBlock.model_validate(data[CODE_TYPE])
        elif data[TYPE_FIELD] == COLUMN_LIST_TYPE:
            block_object = ColumnListBlock.model_validate(data[COLUMN_LIST_TYPE])
        elif data[TYPE_FIELD] == COLUMN_TYPE:
            block_object = ColumnBlock.model_validate(data[COLUMN_TYPE])
        elif data[TYPE_FIELD] == DIVIDER_TYPE:
            block_object = DividerBlock.model_validate(data[DIVIDER_TYPE])
        elif data[TYPE_FIELD] == EMBED_TYPE:
            block_object = EmbedBlock.model_validate(data[EMBED_TYPE])
        elif data[TYPE_FIELD] == EQUATION_TYPE:
            block_object = EquationBlock.model_validate(data[EQUATION_TYPE])
        elif data[TYPE_FIELD] == FILE_TYPE:
            block_object = FileBlock.model_validate(data[FILE_TYPE])
        elif data[TYPE_FIELD] == HEADING_1_TYPE:
            block_object = HeadingOneBlock.model_validate(data[HEADING_1_TYPE])
        elif data[TYPE_FIELD] == HEADING_2_TYPE:
            block_object = HeadingTwoBlock.model_validate(data[HEADING_2_TYPE])
        elif data[TYPE_FIELD] == HEADING_3_TYPE:
            block_object = HeadingThreeBlock.model_validate(data[HEADING_3_TYPE])
        elif data[TYPE_FIELD] == IMAGE_TYPE:
            block_object = ImageBlock.model_validate(data[IMAGE_TYPE])
        elif data[TYPE_FIELD] == LINK_PREVIEW_TYPE:
            block_object = LinkPreviewBlock.model_validate(data[LINK_PREVIEW_TYPE])
        elif data[TYPE_FIELD] == MENTION_TYPE:
            block_object = MentionBlock.model_validate(data[MENTION_TYPE])
        elif data[TYPE_FIELD] == NUMBERED_LIST_TYPE:
            block_object = NumberedListItemBlock.model_validate(
                data[NUMBERED_LIST_TYPE]
            )
        elif data[TYPE_FIELD] == PARAGRAPH_TYPE:
            block_object = ParagraphBlock.model_validate(data[PARAGRAPH_TYPE])
        elif data[TYPE_FIELD] == PDF_TYPE:
            block_object = PDFBlock.model_validate(data[PDF_TYPE])
        elif data[TYPE_FIELD] == QUOTE_TYPE:
            block_object = QuoteBlock.model_validate(data[QUOTE_TYPE])
        elif data[TYPE_FIELD] == SYNCED_BLOCK_TYPE:
            block_object = SyncedBlock.model_validate(data[SYNCED_BLOCK_TYPE])
        elif data[TYPE_FIELD] == TABLE_TYPE:
            block_object = TableBlock.model_validate(data[TABLE_TYPE])
        elif data[TYPE_FIELD] == TABLE_OF_CONTENTS_TYPE:
            block_object = TableOfContentsBlock.model_validate(
                data[TABLE_OF_CONTENTS_TYPE]
            )
        elif data[TYPE_FIELD] == TABLEROW_TYPE:
            block_object = TableRowsBlock.model_validate(data[TABLEROW_TYPE])
        elif data[TYPE_FIELD] == TEMPLATE_TYPE:
            block_object = TemplateBlock.model_validate(data[TEMPLATE_TYPE])
        elif data[TYPE_FIELD] == TODO_TYPE:
            block_object = TodoBlock.model_validate(data[TODO_TYPE])
        elif data[TYPE_FIELD] == TOGGLE_TYPE:
            block_object = ToggleBlock.model_validate(data[TOGGLE_TYPE])
        elif data[TYPE_FIELD] == VIDEO_TYPE:
            block_object = VideoBlock.model_validate(data[VIDEO_TYPE])
        elif data[TYPE_FIELD] == UNSUPPORTED_TYPE:
            block_object = UnsupportedBlock()
        children_list = []
        if CHILDREN_FIELD in data:
            children_list = data[CHILDREN_FIELD]
            data.pop(CHILDREN_FIELD)
        data.pop(data[TYPE_FIELD])
        rtn_instance = Block.model_validate(data)
        rtn_instance.block_object = block_object

        if len(children_list) > 0:
            for child in children_list:
                child_instance = Block.from_dict(child)
                rtn_instance.children.append(child_instance)
        return rtn_instance

    def block_object_to_dict(self, rtn_dict: Dict[str, Any]) -> None:
        if isinstance(self.block_object, BookmarkBlock):
            rtn_dict[BOOKMARK_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, BreadCrumbBlock):
            rtn_dict[BREADCRUMB_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, BulletedListItemBlock):
            rtn_dict[BULLETED_LIST_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, CalloutBlock):
            rtn_dict[CALL_OUT_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, ChildDatabaseBlock):
            rtn_dict[CHILD_DATABASE_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, ChildPageBlock):
            rtn_dict[CHILD_PAGE_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, CodeBlock):
            rtn_dict[CODE_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, ColumnListBlock):
            rtn_dict[COLUMN_LIST_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, ColumnBlock):
            rtn_dict[COLUMN_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, DividerBlock):
            rtn_dict[DIVIDER_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, EmbedBlock):
            rtn_dict[EMBED_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, EquationBlock):
            rtn_dict[EQUATION_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, FileBlock):
            rtn_dict[FILE_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, HeadingOneBlock):
            rtn_dict[HEADING_1_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, HeadingTwoBlock):
            rtn_dict[HEADING_2_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, HeadingThreeBlock):
            rtn_dict[HEADING_3_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, ImageBlock):
            rtn_dict[IMAGE_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, LinkPreviewBlock):
            rtn_dict[LINK_PREVIEW_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, MentionBlock):
            rtn_dict[MENTION_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, NumberedListItemBlock):
            rtn_dict[NUMBERED_LIST_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, ParagraphBlock):
            rtn_dict[PARAGRAPH_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, PDFBlock):
            rtn_dict[PDF_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, QuoteBlock):
            rtn_dict[QUOTE_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, SyncedBlock):
            rtn_dict[SYNCED_BLOCK_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, TableBlock):
            rtn_dict[TABLE_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, TableOfContentsBlock):
            rtn_dict[TABLE_OF_CONTENTS_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, TableRowsBlock):
            rtn_dict[TABLEROW_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, TemplateBlock):
            rtn_dict[TEMPLATE_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, TodoBlock):
            rtn_dict[TODO_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, ToggleBlock):
            rtn_dict[TOGGLE_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, VideoBlock):
            rtn_dict[VIDEO_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]
        elif isinstance(self.block_object, UnsupportedBlock):
            rtn_dict[UNSUPPORTED_TYPE] = rtn_dict[BLOCK_OBJECT_FIELD]

    def to_dict(self) -> Dict[str, Any]:
        rtn_dict = Block.model_dump(self, exclude={CHILDREN_FIELD})
        self.block_object_to_dict(rtn_dict)
        rtn_dict.pop(BLOCK_OBJECT_FIELD)

        rtn_dict[CHILDREN_FIELD] = []
        if len(self.children) > 0:
            for child in self.children:
                child_dict = child.to_dict()
                rtn_dict[CHILDREN_FIELD].append(child_dict)
        return rtn_dict

    def child_database_to_text(self, notion: Client) -> str:
        results = notion.databases.retrieve(self.id)
        database = Database.from_dict(results)
        columns = database.get_columns()
        results = notion.databases.query(self.id)
        results_list = []
        for result in results["results"]:
            properties = result["properties"]
            row_list = []
            for key in properties:
                column = key
                column_type = properties[key]["type"]
                column_data = properties[key][column_type]
                row_list.append(
                    DatabaseQueryResult.from_dict(column_type, column, column_data)
                )
            results_list.append(row_list)
        query_results = DatabaseQueryResults(
            columns=columns,
            description=database.get_description(),
            results=results_list,
        )
        rtn_text = f"{self.block_object.title}\n{query_results.to_text()}"
        return rtn_text

    def block_object_to_text(self, notion: Client) -> str:
        if isinstance(self.block_object, ChildDatabaseBlock):
            return self.child_database_to_text(notion)
        else:
            return self.block_object.to_text()
