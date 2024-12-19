from dataclasses import dataclass
from typing import Any, Dict

from leettools.core.schemas.api_provider_config import BaseAPIProviderConfigSchema


@dataclass
class APIProviderConfigDuckDBSchema(BaseAPIProviderConfigSchema):
    """
    DuckDB schema definition for API provider config.
    """

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return cls.get_base_columns()
