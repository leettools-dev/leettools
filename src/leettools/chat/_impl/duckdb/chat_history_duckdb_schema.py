from dataclasses import dataclass
from typing import Dict

from leettools.chat.schemas.chat_history import BaseChatHistorySchema


@dataclass
class ChatHistoryDuckDBSchema(BaseChatHistorySchema):
    """DuckDB-specific schema for chat history."""

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        """Get DuckDB column definitions."""
        return cls.get_base_columns()
