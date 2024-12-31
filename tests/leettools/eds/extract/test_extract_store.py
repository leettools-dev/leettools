from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.common.utils import time_utils
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.extract.extract_store import (
    EXTRACT_DB_SOURCE_FIELD,
    EXTRACT_DB_TIMESTAMP_FIELD,
    create_extract_store,
)
from leettools.eds.rag.search.filter import BaseCondition, Filter


def test_extract_store(tmp_path):

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(tmp_path, context, org, kb, user)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)
            logger().info(f"Finished test for store_types: {store_types}")


def _test_function(tmp_path, context: Context, org: Org, kb: KnowledgeBase, user: User):

    class ExampleModel(BaseModel):
        name: str = Field(..., json_schema_extra={"primary_key": True})
        age: int
        height: Optional[float] = 1.0
        email: Union[str, None] = Field(None, json_schema_extra={"index": True})
        active: bool
        metadata: Dict[str, Any]
        aliases: Optional[List[str]]
        created_at: Optional[datetime]
        created_timestamp_in_ms: Optional[int]

    extract_store = create_extract_store(
        context, org, kb, "example_model", ExampleModel
    )

    extended_model = extract_store.get_actual_model()
    fields = extended_model.model_fields.keys()

    assert "name" in fields
    assert "age" in fields
    assert "height" in fields
    assert "email" in fields
    assert "active" in fields
    assert "metadata" in fields
    assert "aliases" in fields
    assert "created_at" in fields
    assert "created_timestamp_in_ms" in fields
    assert EXTRACT_DB_SOURCE_FIELD in fields
    assert EXTRACT_DB_TIMESTAMP_FIELD in fields

    records = extract_store.get_records()
    assert len(records) == 0

    record_01 = ExampleModel(
        name="test_name_01",
        age=30,
        height=5.5,
        email="test_email_01",
        active=True,
        metadata={"key": "value"},
        aliases=["alias1", "alias2"],
        created_at=datetime.now(),
        created_timestamp_in_ms=time_utils.cur_timestamp_in_ms(),
    )

    record_02 = ExampleModel(
        name="test_name_02",
        age=40,
        email="test_email_02",
        active=False,
        metadata={"key": "value"},
        aliases=["alias1", "alias2"],
        created_at=datetime.now(),
        created_timestamp_in_ms=time_utils.cur_timestamp_in_ms(),
    )

    records = extract_store.save_records(
        [record_01, record_02], {EXTRACT_DB_SOURCE_FIELD: "test_source"}
    )
    assert len(records) == 2
    assert type(records[0]) == extended_model

    records = extract_store.get_records()
    assert len(records) == 2
    assert type(records[0]) == extended_model

    filter = BaseCondition(field="name", operator="==", value="test_name_01")
    records = extract_store.get_records(filter=filter)
    assert len(records) == 1
    assert type(records[0]) == extended_model
    assert records[0].name == "test_name_01"
    assert records[0].age == 30

    filter = BaseCondition(field="name", operator="==", value="test_name_xyz")
    records = extract_store.get_records(filter=filter)
    assert len(records) == 0

    filter = Filter(
        relation="or",
        conditions=[
            BaseCondition(field="name", operator="==", value="test_name_01"),
            BaseCondition(field="age", operator=">", value=35),
        ],
    )
    records = extract_store.get_records(filter=filter)
    assert len(records) == 2

    filter = BaseCondition(field="name", operator="==", value="test_name_01")
    extract_store.delete_records(filter=filter)

    records = extract_store.get_records()
    assert len(records) == 1
    assert records[0].name == "test_name_02"

    filter = Filter(
        relation="or",
        conditions=[
            BaseCondition(field="name", operator="==", value="test_name_01"),
            BaseCondition(field="age", operator=">", value=35),
        ],
    )
    records = extract_store.get_records(filter=filter)
    assert len(records) == 1
    assert records[0].name == "test_name_02"

    extract_store.delete_records()
    records = extract_store.get_records()
    assert len(records) == 0
