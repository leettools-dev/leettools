from leettools.common.logging import logger
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.user import User
from leettools.core.strategy._impl.duckdb.strategy_store_duckdb import (
    StrategyStoreDuckDB,
)
from leettools.core.strategy.schemas.strategy import Strategy, StrategyCreate
from leettools.core.strategy.schemas.strategy_status import StrategyStatus


def test_strategy_store():

    context = ContextManager().get_context()  # type: Context
    context.reset(is_test=True)
    user_store = context.get_user_store()
    prompt_store = context.get_prompt_store()
    intention_store = context.get_intention_store()
    strategy_store = StrategyStoreDuckDB(
        context.settings, prompt_store, intention_store, user_store
    )
    try:
        _test_function(context, strategy_store)
    except Exception as e:
        logger().error(f"Error: {e}")
        raise e
    finally:
        strategy_store._reset_for_test()


def _test_function(context: Context, strategy_store: StrategyStoreDuckDB):

    strategy_create = StrategyCreate(strategy_name="test_strategy")

    admin_user = context.get_user_store().get_user_by_name(User.ADMIN_USERNAME)

    strategies = strategy_store.list_active_strategies_for_user(user=admin_user)
    num_of_system_strategies = len(strategies)

    # Test create_strategy
    strategy: Strategy = strategy_store.create_strategy(
        strategy_create=strategy_create, user=admin_user
    )
    assert strategy.strategy_id is not None
    assert strategy.strategy_status == StrategyStatus.ACTIVE.value

    logger().info(f"Created strategy with ID: {strategy.strategy_id}")

    # Test get_strategy
    strategy_id = strategy.strategy_id
    strategy_retrieved = strategy_store.get_strategy_by_id(strategy_id)
    assert strategy_retrieved is not None
    assert strategy_retrieved.strategy_id == strategy_id
    logger().info(f"Retrieved strategy with ID: {strategy.strategy_id}")

    # Test list_strategies
    strategies = strategy_store.list_active_strategies_for_user(user=admin_user)
    assert len(strategies) == num_of_system_strategies + 1
    logger().info(f"Listed {len(strategies)} strategies")

    strategy_create = StrategyCreate(
        strategy_name="test_strategy", strategy_sections={}, strategy_description=""
    )
    strategy_2: Strategy = strategy_store.create_strategy(
        strategy_create=strategy_create, user=admin_user
    )
    assert strategy_2.strategy_id is not None
    assert strategy_2.strategy_status == StrategyStatus.ACTIVE.value
    assert strategy_2.strategy_id != strategy_id

    strategies = strategy_store.list_active_strategies_for_user(user=admin_user)
    assert len(strategies)

    strategy_get = strategy_store.get_active_strategy_by_name(
        strategy_name="test_strategy", user=admin_user
    )
    assert strategy_get.strategy_id == strategy_2.strategy_id

    strategy_archived = strategy_store.get_strategy_by_id(strategy_id)
    assert strategy_archived.strategy_status == StrategyStatus.ARCHIVED
    assert strategy_archived.strategy_id == strategy_id

    # Test set_strategy_status
    strategy_status = StrategyStatus.DISABLED
    strategy_updated = strategy_store.set_strategy_status_by_id(
        strategy_id, strategy_status
    )
    assert strategy_updated.strategy_status == strategy_status

    strategy_check = strategy_store.get_strategy_by_id(strategy_id)
    assert strategy_check.strategy_status == strategy_status

    strategies = strategy_store.list_active_strategies_for_user(user=admin_user)
    assert len(strategies) == num_of_system_strategies + 1
    logger().info(f"Listed {len(strategies)} strategies")
    assert strategies[0].strategy_name == "default"
    assert (
        strategies[0].strategy_name
        == strategy_store.get_default_strategy().strategy_name
    )
