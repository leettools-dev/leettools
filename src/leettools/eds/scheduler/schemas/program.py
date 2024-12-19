from enum import Enum
from typing import List, Union

from pydantic import BaseModel

from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document
from leettools.core.schemas.segment import Segment


class ProgramType(str, Enum):
    CONNECTOR = "connector"
    CONVERT = "convert"
    SPLIT = "split"
    EMBED = "embed"
    ENTITY = "entity"


class ProgramTypeDescrtion(BaseModel):
    type: ProgramType
    display_name: str
    description: str


class ConnectorProgramSpec(BaseModel):
    org_id: str
    kb_id: str
    source: DocSource


class ConvertProgramSpec(BaseModel):
    org_id: str
    kb_id: str
    source: DocSink


class EmbedProgramSpec(BaseModel):
    org_id: str
    kb_id: str
    source: List[Segment]


class SplitProgramSpec(BaseModel):
    org_id: str
    kb_id: str
    source: Document


class ProgramSpec(BaseModel):
    """
    The Program spec should be environment agnostic.
    """

    program_type: ProgramType
    real_program_spec: Union[
        ConnectorProgramSpec, ConvertProgramSpec, SplitProgramSpec, EmbedProgramSpec
    ]

    @classmethod
    def get_program_type_descriptions(cls) -> List[ProgramTypeDescrtion]:
        return [
            ProgramTypeDescrtion(
                type=ProgramType.CONNECTOR,
                display_name="Connector",
                description="Connectors are used to connect to a data source and pull in documents.",
            ),
            ProgramTypeDescrtion(
                type=ProgramType.CONVERT,
                display_name="Convert",
                description="Converters are used to convert documents from the original format to markdown.",
            ),
            ProgramTypeDescrtion(
                type=ProgramType.SPLIT,
                display_name="Split",
                description="Splitters are used to split documents into segments and create document graph.",
            ),
            ProgramTypeDescrtion(
                type=ProgramType.EMBED,
                display_name="Embed",
                description="Embedders are used to embed segments into vector databases.",
            ),
            ProgramTypeDescrtion(
                type=ProgramType.ENTITY,
                display_name="Entity",
                description="Entity extractors are used to extract entities from documents.",
            ),
        ]
