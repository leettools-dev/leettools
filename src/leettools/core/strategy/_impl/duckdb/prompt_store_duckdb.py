import hashlib
import json
import uuid
from datetime import datetime
from typing import List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.exceptions import EntityNotFoundException
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.core.strategy._impl.duckdb.prompt_store_ducksb_schema import (
    PromptDuckDBSchema,
)
from leettools.core.strategy.prompt_store import AbstractPromptStore
from leettools.core.strategy.schemas.prompt import (
    Prompt,
    PromptCategory,
    PromptCreate,
    PromptStatus,
    PromptType,
)
from leettools.settings import SystemSettings


class PromptStoreDuckDB(AbstractPromptStore):
    """
    PromptStoreDuckDB is a PromptStore implementation using DuckDB as the backend.
    """

    def __init__(self, settings: SystemSettings) -> None:
        """Initialize DuckDB connection."""
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)

    def _dict_to_prompt(self, data: dict) -> Prompt:
        """Convert stored dictionary to Prompt."""
        # JSON decode lists/dicts
        if data.get(Prompt.FIELD_PROMPT_VARIABLES):
            try:
                data[Prompt.FIELD_PROMPT_VARIABLES] = json.loads(
                    data[Prompt.FIELD_PROMPT_VARIABLES]
                )
            except json.JSONDecodeError:
                logger().warning("Failed to decode prompt variables JSON")
                data[Prompt.FIELD_PROMPT_VARIABLES] = None
        return Prompt.model_validate(data)

    def _get_table_name(self) -> str:
        """Get the table name for the prompts."""
        return self.duckdb_client.create_table_if_not_exists(
            self.settings.DB_COMMOM,
            self.settings.COLLECTION_PROMPT,
            PromptDuckDBSchema.get_schema(),
        )

    def _prompt_to_dict(self, prompt: Prompt) -> dict:
        prompt_dict = prompt.model_dump()
        if Prompt.FIELD_PROMPT_VARIABLES in prompt_dict:
            prompt_dict[Prompt.FIELD_PROMPT_VARIABLES] = json.dumps(
                prompt_dict[Prompt.FIELD_PROMPT_VARIABLES]
            )
        return prompt_dict

    def create_prompt(self, prompt_create: PromptCreate) -> Prompt:
        """Create a prompt in the store."""
        prompt_create_dict = prompt_create.model_dump()
        prompt_create_str = json.dumps(prompt_create_dict, sort_keys=True)
        prompt_hash = hashlib.sha256(prompt_create_str.encode()).hexdigest()

        # Check if prompt already exists
        table_name = self._get_table_name()
        where_clause = f"WHERE {Prompt.FIELD_PROMPT_HASH} = ?"
        value_list = [prompt_hash]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if result is not None:
            logger().noop(
                f"Found existing prompt with the same values hash: {prompt_create_str}"
            )
            return self._dict_to_prompt(result)

        current_time = time_utils.current_datetime()
        prompt_dict = self._prompt_to_dict(prompt_create)
        prompt_id = str(uuid.uuid4())
        prompt_dict[Prompt.FIELD_PROMPT_ID] = prompt_id
        prompt_dict[Prompt.FIELD_PROMPT_HASH] = prompt_hash
        prompt_dict[Prompt.FIELD_PROMPT_STATUS] = PromptStatus.PRODUCTION
        prompt_dict[Prompt.FIELD_CREATED_AT] = current_time
        prompt_dict[Prompt.FIELD_UPDATED_AT] = current_time

        # Insert new prompt
        column_list = list(prompt_dict.keys())
        value_list = list(prompt_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )
        return self.get_prompt(prompt_id)

    def get_prompt(self, prompt_id: str) -> Prompt:
        """Get a prompt from the store."""
        table_name = self._get_table_name()
        where_clause = f"WHERE {Prompt.FIELD_PROMPT_ID} = ?"
        value_list = [prompt_id]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if result is None:
            raise EntityNotFoundException(
                entity_name=f"Prompt {prompt_id}", entity_type="Prompt"
            )
        return self._dict_to_prompt(result)

    def set_prompt_status(self, prompt_id: str, status: PromptStatus) -> Prompt:
        """Set the status of a prompt in the store."""
        table_name = self._get_table_name()
        column_list = [Prompt.FIELD_PROMPT_STATUS, Prompt.FIELD_UPDATED_AT]
        value_list = [status, time_utils.current_datetime()]
        where_clause = f"WHERE {Prompt.FIELD_PROMPT_ID} = ?"
        value_list = value_list + [prompt_id]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_prompt(prompt_id)

    def list_prompts(self) -> List[Prompt]:
        """List all prompts in the store."""
        table_name = self._get_table_name()
        results = self.duckdb_client.fetch_all_from_table(table_name=table_name)
        return [self._dict_to_prompt(result) for result in results]

    def list_prompts_by_filter(
        self,
        category: Optional[PromptCategory],
        type: Optional[PromptType],
        status: Optional[PromptStatus],
    ) -> List[Prompt]:
        """List prompts by category, type, and status."""
        conditions = []
        params = []

        if category:
            conditions.append(f"{Prompt.FIELD_PROMPT_CATEGORY} = ?")
            params.append(category)
        if type:
            conditions.append(f"{Prompt.FIELD_PROMPT_TYPE} = ?")
            params.append(type)
        if status:
            conditions.append(f"{Prompt.FIELD_PROMPT_STATUS} = ?")
            params.append(status)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        table_name = self._get_table_name()
        where_clause = f"WHERE {where_clause}"
        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=params,
        )
        return [self._dict_to_prompt(result) for result in results]

    def _reset_for_test(self):
        """Reset the collection for testing."""
        if self.settings.COLLECTION_PROMPT.endswith("_test"):
            table_name = self._get_table_name()
            self.duckdb_client.delete_from_table(table_name=table_name)
