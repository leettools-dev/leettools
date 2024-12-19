from pydantic import BaseModel, Field

from leettools.common.utils.obj_utils import add_fieldname_constants


@add_fieldname_constants
class Chunk(BaseModel):
    """
    Represents a chunk of text in a document.
    """

    content: str = Field(..., description="The content of the chunk.")
    heading: str = Field(..., description="The heading of the chunk.")
    position_in_doc: str = Field(
        ..., description="The position of the chunk in the document, such as '2.3.3'."
    )
    start_offset: int = Field(..., description="The start offset of the chunk.")
    end_offset: int = Field(..., description="The end offset of the chunk.")
