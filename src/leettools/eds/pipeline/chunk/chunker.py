from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.schemas.chunk import Chunk
from leettools.settings import SystemSettings


class AbstractChunker(ABC):
    """
    The AbstractChunker is responsible for chunking text.
    """

    @abstractmethod
    def chunk(self, text: str) -> List[Chunk]:
        """
        Chunk the text.

        Args:
        text: The text to chunk.

        Returns:
        The chunked text.
        """
        pass


def create_chunker(
    settings: SystemSettings, module_name: Optional[str] = None
) -> AbstractChunker:
    # Construct the target module name using the current package
    import os

    from leettools.common.utils import factory_util

    if module_name is None or module_name == "":
        module_name = os.environ.get(SystemSettings.EDS_DEFAULT_CHUNKER)
        if module_name is None or module_name == "":
            module_name = settings.DEFAULT_CHUNKER

    if "." not in module_name:
        module_name = f"{__package__}._impl.{module_name}"

    return factory_util.create_object(
        module_name,
        AbstractChunker,
        settings=settings,
    )
