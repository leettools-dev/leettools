from leettools.common.exceptions import EntityNotFoundException
from leettools.common.logging import logger
from leettools.context_manager import Context, ContextManager
from leettools.core.strategy._impl.duckdb.intention_store_duckdb import (
    IntentionStoreDuckDB,
)
from leettools.core.strategy.schemas.intention import IntentionCreate, IntentionUpdate


def test_intention_store_duckdb():

    context = ContextManager().get_context()  # type: Context
    context.reset(is_test=True)
    intention_store = IntentionStoreDuckDB(context.settings)

    try:
        _test_function(intention_store)
    except Exception as e:
        logger().error(f"Error: {e}")
        raise e
    finally:
        intention_store._reset_for_test()


def _test_function(intention_store: IntentionStoreDuckDB):

    intention_list = intention_store.get_all_intentions()
    system_intention_count = len(intention_list)

    intention_name_1 = "test_intention_1"
    intention_name_2 = "test_intention_2"

    intention_create_1 = IntentionCreate(intention=intention_name_1)
    intention_1 = intention_store.create_intention(intention_create_1)
    assert intention_1.intention == intention_name_1
    assert intention_1.display_name == intention_name_1
    assert intention_1.is_active == True
    assert intention_1.created_at == intention_1.updated_at

    intention_list = intention_store.get_all_intentions()
    assert len(intention_list) == system_intention_count + 1
    assert intention_list[system_intention_count].intention == intention_name_1

    intention_create_2 = IntentionCreate(
        intention=intention_name_2,
        display_name=intention_name_2,
        description="test description",
        examples=["example1", "example2"],
        is_active=True,
    )
    intention_2 = intention_store.create_intention(intention_create_2)
    assert intention_2.intention == intention_name_2
    assert intention_2.display_name == intention_name_2
    assert intention_2.is_active == True
    assert intention_2.created_at == intention_2.updated_at
    assert intention_2.description == "test description"
    assert intention_2.examples == ["example1", "example2"]

    intention_list = intention_store.get_all_intentions()
    assert len(intention_list) == system_intention_count + 2

    intention_retrieved_1 = intention_store.get_intention_by_name(intention_name_1)
    assert intention_retrieved_1.intention == intention_name_1

    intention_update: IntentionUpdate = intention_retrieved_1.model_copy()
    intention_update.examples = ["example3", "example4"]

    intention_1_updated = intention_store.update_intention(intention_update)
    assert intention_1_updated.intention == intention_name_1
    assert intention_1_updated.display_name == intention_name_1
    assert intention_1_updated.updated_at > intention_1.updated_at
    assert intention_1_updated.examples == ["example3", "example4"]

    intention_update = IntentionUpdate(
        intention="random_intention",
        display_name="test display name",
    )
    try:
        intention_store.update_intention(intention_update)
        raise Exception("Should not reach here")
    except Exception as e:
        assert type(e) == EntityNotFoundException

    intention_2_update: IntentionUpdate = intention_2.model_copy()
    intention_2_update.examples = ["example5"]
    intention_2_update.is_active = False

    intention_2_updated = intention_store.update_intention(intention_2_update)
    assert intention_2_updated.intention == intention_name_2
    assert intention_2_updated.examples == ["example5"]
    assert intention_2_updated.is_active == False

    intention_list = intention_store.get_all_intentions()
    assert len(intention_list) == system_intention_count + 2
