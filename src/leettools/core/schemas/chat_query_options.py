from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ChatQueryOptions(BaseModel):
    """
    The query options, including two parts:
    1. generic options for all the queries that is not specific to any query flow
    2. flow_options for the specific query flows
    """

    # Right now no generic options are defined.

    # Right now flow_type and flow_options are not typed or limited to our
    # predefined flow type.
    flow_options: Optional[Dict[str, Any]] = Field(
        {}, description="Options for the query flows."
    )
