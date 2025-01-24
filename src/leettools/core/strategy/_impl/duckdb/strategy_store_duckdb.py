import hashlib
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.exceptions import (
    EntityExistsException,
    UnexpectedOperationFailureException,
)
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.common.utils.template_eval import find_template_variables
from leettools.core.schemas.user import User
from leettools.core.strategy._impl.duckdb.strategy_store_ducksb_schema import (
    StrategyDuckDBSchema,
)
from leettools.core.strategy.intention_store import AbstractIntentionStore
from leettools.core.strategy.prompt_store import AbstractPromptStore
from leettools.core.strategy.schemas.intention import IntentionCreate, IntentionUpdate
from leettools.core.strategy.schemas.prompt import (
    Prompt,
    PromptCategory,
    PromptCreate,
    PromptType,
)
from leettools.core.strategy.schemas.strategy import (
    Strategy,
    StrategyCreate,
    convert_strategy_conf_create,
)
from leettools.core.strategy.schemas.strategy_conf import (
    StrategyConf,
    StrategyConfCreate,
)
from leettools.core.strategy.schemas.strategy_status import StrategyStatus
from leettools.core.strategy.strategy_store import AbstractStrategyStore
from leettools.core.user.user_store import AbstractUserStore
from leettools.settings import SystemSettings

script_path = os.path.dirname(os.path.realpath(__file__))


class StrategyStoreDuckDB(AbstractStrategyStore):
    """
    StrategyStoreDuckDB is a StrategyStore implementation using DuckDB as the backend.
    """

    def __init__(
        self,
        settings: SystemSettings,
        prompt_store: AbstractPromptStore,
        intention_store: AbstractIntentionStore,
        user_store: AbstractUserStore,
        run_init: bool = True,
    ) -> None:
        """
        Initialize the DuckDB StrategyStore.
        """
        logger().info("Initializing the DuckDB StrategyStore.")
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)

        self.admin_user = user_store.get_user_by_name(User.ADMIN_USERNAME)
        if self.admin_user is None:
            raise UnexpectedOperationFailureException(
                operation_desc="Get admin user",
                error=f"Failed to get the admin user {User.ADMIN_USERNAME}.",
            )

        self.prompt_store = prompt_store
        self.intention_store = intention_store

        self.predefined_path = os.path.join(script_path, "../../predefined")
        self.default_path = os.path.join(self.predefined_path, "default")

        if run_init:
            self._run_init()
        else:
            logger().info("Skip reading the strategy path.")
            self.default_strategy = self.get_active_strategy_by_name(
                strategy_name="default", user=self.admin_user
            )

        logger().info("Successfully initialized the DuckDB StrategyStore.")

    def _archive_strategy(self, strategy: Strategy) -> Strategy:
        """
        Archive the strategy in the store.
        """
        table_name = self._get_table_name()
        column_list = [Strategy.FIELD_STRATEGY_STATUS, Strategy.FIELD_UPDATED_AT]
        value_list = [StrategyStatus.ARCHIVED.value, time_utils.current_datetime()]
        where_clause = f"WHERE {Strategy.FIELD_STRATEGY_ID} = '{strategy.strategy_id}'"
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_strategy_by_id(strategy.strategy_id)

    def _create_prompt_from_file(
        self, file: str, cat: PromptCategory, type: PromptType
    ) -> Prompt:
        with open(file, "r", encoding="utf-8") as f:
            prompt_text = f.read()

            variables: Dict[str, Any] = {}
            for v in find_template_variables(prompt_text):
                variables[v] = None

            prompt_create: PromptCreate = PromptCreate(
                prompt_category=cat,
                prompt_type=type,
                prompt_template=prompt_text,
                prompt_variables=variables,
            )
            return self.prompt_store.create_prompt(prompt_create)

    def _dict_to_strategy(self, data: dict) -> Strategy:
        if Strategy.FIELD_STRATEGY_SECTIONS in data:
            data[Strategy.FIELD_STRATEGY_SECTIONS] = json.loads(
                data[Strategy.FIELD_STRATEGY_SECTIONS]
            )
        return Strategy.model_validate(data)

    def _get_file_with_default(self, path: str, filename: str) -> str:
        target_file = os.path.join(path, filename)
        if os.path.exists(target_file):
            logger().noop(f"Found {filename} file.")
        else:
            logger().noop(f"No {filename} file found, using the default.")
            target_file = os.path.join(self.default_path, filename)
        return target_file

    def _get_table_name(self) -> str:
        return self.duckdb_client.create_table_if_not_exists(
            self.settings.DB_COMMOM,
            self.settings.COLLECTION_STRATEGY,
            StrategyDuckDBSchema.get_schema(),
        )

    def _list_strategies_by_filter(self, filter: Dict[str, Any]) -> List[Strategy]:
        """
        List all the strategies in the store by the filter. Right now the filter can only
        specify the status.
        """
        table_name = self._get_table_name()
        logger().debug("The filter is " + str(filter))
        where_clause = " AND ".join([f"{k} = ?" for k, v in filter.items()])
        where_clause = f"WHERE {where_clause}"
        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=list(filter.values()),
        )
        return [self._dict_to_strategy(result) for result in results]

    def _read_path_for_strategy(self, path: str):
        # scan the path for any strategy directories
        for root, dirs, files in os.walk(path):
            for dir in dirs:
                if dir != "default":
                    # if there is a chat_strategy.json file under the directory, create the strategy
                    if os.path.exists(os.path.join(root, dir, "chat_strategy.json")):
                        self.create_strategy_from_path(os.path.join(root, dir))
                    else:
                        # no chat_strategy.json file, skip the directory
                        pass
                else:
                    # already processed
                    pass

    def _reset_for_test(self):
        if self.settings.DUCKDB_FILE.endswith("_test.db"):
            table_name = self._get_table_name()
            self.duckdb_client.delete_from_table(table_name=table_name)

    def _run_init(self):
        self.default_strategy = self.create_strategy_from_path(self.default_path)
        self._read_path_for_strategy(self.predefined_path)
        if self.settings.STRATEGY_PATH is not None:
            for target_path in self.settings.STRATEGY_PATH.split(","):
                logger().info(f"Reading extra strategies from path {target_path}.")
                self._read_path_for_strategy(target_path)

    def create_strategy(
        self, strategy_create: StrategyCreate, user: User
    ) -> StrategyConf:
        if user is None:
            user = self.admin_user

        if strategy_create.user_uuid is None:
            strategy_create.user_uuid = user.user_uuid
        else:
            if strategy_create.user_uuid != user.user_uuid:
                raise UnexpectedOperationFailureException(
                    operation_desc="Create strategy",
                    error=f"The user uuid in the strategy {strategy_create.user_uuid} "
                    f"does not match the user {user.user_uuid}.",
                )

        strategy_create_dict = strategy_create.model_dump()
        strategy_create_str = json.dumps(strategy_create_dict, sort_keys=True)
        strategy_hash = hashlib.sha256(strategy_create_str.encode()).hexdigest()
        logger().noop(f"Creating strategy: {strategy_create} with hash {strategy_hash}")
        table_name = self._get_table_name()
        where_clause = (
            f"WHERE {Strategy.FIELD_USER_UUID} = '{user.user_uuid}' "
            f"AND {Strategy.FIELD_STRATEGY_HASH} = '{strategy_hash}'"
        )
        existing_same_hash = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
        )
        active_same_name = self.get_active_strategy_by_name(
            strategy_name=strategy_create.strategy_name, user=user
        )

        if existing_same_hash is not None:
            logger().debug(
                f"Found existing strategy with the same values hash: {strategy_create_str}"
            )
            existing_strategy = self._dict_to_strategy(existing_same_hash)
            if active_same_name is not None:
                if existing_strategy.strategy_id == active_same_name.strategy_id:
                    logger().debug(
                        f"The existing strategy is the same as the active strategy: {strategy_create.strategy_name}"
                    )
                    return active_same_name
                else:
                    logger().debug(
                        f"The existing strategy is different from the active strategy with "
                        f"the same name: {strategy_create.strategy_name}, "
                        "archive the active strategy and set the existing strategy to active."
                    )
                    self._archive_strategy(active_same_name)
                    self.set_strategy_status_by_id(
                        existing_strategy.strategy_id, StrategyStatus.ACTIVE
                    )
                    return self.get_strategy_by_id(existing_strategy.strategy_id)
            else:
                logger().debug(
                    f"No active strategy is found with the same name: {strategy_create.strategy_name}, "
                    "set the existing strategy to active."
                )
                self.set_strategy_status_by_id(
                    existing_strategy.strategy_id, StrategyStatus.ACTIVE
                )
                return self.get_strategy_by_id(existing_strategy.strategy_id)

        logger().debug("No existing strategy with the same hash.")
        if active_same_name is not None:
            logger().debug(
                f"Found active strategy with the same name but not same hash:"
                f"{strategy_create.strategy_name}, archive the active strategy."
            )
            self._archive_strategy(active_same_name)

        strategy_dict = strategy_create.model_dump()
        if Strategy.FIELD_STRATEGY_SECTIONS in strategy_dict:
            strategy_dict[Strategy.FIELD_STRATEGY_SECTIONS] = json.dumps(
                strategy_dict[Strategy.FIELD_STRATEGY_SECTIONS]
            )
        strategy_dict[Strategy.FIELD_STRATEGY_ID] = str(uuid.uuid4())
        strategy_dict[Strategy.FIELD_STRATEGY_STATUS] = StrategyStatus.ACTIVE.value
        strategy_dict[Strategy.FIELD_STRATEGY_HASH] = strategy_hash
        current_time = time_utils.current_datetime()
        strategy_dict[Strategy.FIELD_STRATEGY_VERSION] = current_time.strftime(
            "%Y%m%d-%H%M%S"
        )
        strategy_dict[Strategy.FIELD_CREATED_AT] = current_time
        strategy_dict[Strategy.FIELD_UPDATED_AT] = current_time
        if user.user_uuid == self.admin_user.user_uuid:
            strategy_dict[Strategy.FIELD_IS_SYSTEM] = True
        else:
            strategy_dict[Strategy.FIELD_IS_SYSTEM] = False

        column_list = list(strategy_dict.keys())
        value_list = list(strategy_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )
        logger().noop(f"Created strategy: {strategy_create}")
        return self.get_strategy_by_id(strategy_dict[Strategy.FIELD_STRATEGY_ID])

    def create_strategy_from_path(
        self, path_str: str, user: Optional[User] = None
    ) -> Strategy:
        """Add a local directory to repository."""
        if not os.path.isabs(path_str):
            path = os.path.abspath(path_str)
        else:
            path = os.path.join(script_path, path_str)

        if not os.path.exists(path):
            logger().error(f"The path {path} does not exist.")
            return None

        logger().noop(f"Creating strategy from {path}")

        # read the chat_strategy.json file
        # TODO: should change to the new format
        json_file = self._get_file_with_default(path, "chat_strategy.json")
        with open(json_file, "r", encoding="utf-8") as f:
            chat_strategy_create = StrategyConfCreate.model_validate_json(f.read())

        if user is None:
            user = self.admin_user

        chat_strategy_create.user_uuid = user.user_uuid

        # read the intention list file and use only line with content
        # ignore the lines started with # and empty lines
        # strip the leading and trailing spaces
        intention_list_file = self._get_file_with_default(path, "intention_list.txt")
        with open(intention_list_file, "r", encoding="utf-8") as f:
            chat_strategy_create.intention_list = [
                line.strip()
                for line in f.readlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        logger().noop(f"The intention list is {chat_strategy_create.intention_list}")

        # TODO: should add more information to the intention configuration
        for intention in chat_strategy_create.intention_list:
            try:
                self.intention_store.create_intention(
                    IntentionCreate(
                        intention=intention,
                        is_active=True,
                    )
                )
            except EntityExistsException:
                logger().noop(f"Intention {intention} already exists.")
                existing_intention = self.intention_store.get_intention_by_name(
                    intention
                )
                # TODO: we should only update the intention if it has been changed.
                self.intention_store.update_intention(
                    IntentionUpdate(
                        intention=intention,
                        is_active=True,
                    )
                )

        # read the intention prompts
        intention_sp_file = self._get_file_with_default(path, "intention_sp.txt")
        intention_sp = self._create_prompt_from_file(
            intention_sp_file, PromptCategory.INTENTION, PromptType.SYSTEM
        )
        chat_strategy_create.intention_sp_id = intention_sp.prompt_id

        intention_up_file = self._get_file_with_default(path, "intention_up.txt")
        intention_up = self._create_prompt_from_file(
            intention_up_file, PromptCategory.INTENTION, PromptType.USER
        )
        chat_strategy_create.intention_up_id = intention_up.prompt_id

        # read the rewrite prompts based on their intentions
        chat_strategy_create.intention_list.insert(0, "default")
        for intention in chat_strategy_create.intention_list:
            rewrite_sp_file = self._get_file_with_default(
                path, f"rewrite_sp_{intention}.txt"
            )
            if os.path.exists(rewrite_sp_file):
                rewrite_sp = self._create_prompt_from_file(
                    rewrite_sp_file, PromptCategory.REWRITE, PromptType.SYSTEM
                )
                chat_strategy_create.rewrite_sp_ids[intention] = rewrite_sp.prompt_id
            else:
                logger().noop(
                    f"No rewrite_sp_{intention}.txt file found, using default."
                )
                chat_strategy_create.rewrite_sp_ids[intention] = (
                    chat_strategy_create.rewrite_sp_ids["default"]
                )

            rewrite_up_file = self._get_file_with_default(
                path, f"rewrite_up_{intention}.txt"
            )
            if os.path.exists(rewrite_up_file):
                rewrite_up = self._create_prompt_from_file(
                    rewrite_up_file, PromptCategory.REWRITE, PromptType.SYSTEM
                )
                chat_strategy_create.rewrite_up_ids[intention] = rewrite_up.prompt_id
            else:
                logger().noop(
                    f"No rewrite_up_{intention}.txt file found, using default."
                )
                chat_strategy_create.rewrite_up_ids[intention] = (
                    chat_strategy_create.rewrite_up_ids["default"]
                )

        # read the system prompts for the final question submission
        for intention in chat_strategy_create.intention_list:
            system_prompt_file = self._get_file_with_default(
                path, f"inference_sp_{intention}.txt"
            )
            if os.path.exists(system_prompt_file):
                system_prompt = self._create_prompt_from_file(
                    system_prompt_file, PromptCategory.INFERENCE, PromptType.SYSTEM
                )
                chat_strategy_create.system_prompt_ids[intention] = (
                    system_prompt.prompt_id
                )
            else:
                logger().noop(
                    f"No system_prompt_{intention}.txt file found, using default."
                )
                chat_strategy_create.system_prompt_ids[intention] = (
                    chat_strategy_create.system_prompt_ids["default"]
                )

            user_prompt_file = self._get_file_with_default(
                path, f"inference_up_{intention}.txt"
            )
            if os.path.exists(user_prompt_file):
                user_prompt = self._create_prompt_from_file(
                    user_prompt_file, PromptCategory.INFERENCE, PromptType.USER
                )
                chat_strategy_create.user_prompt_ids[intention] = user_prompt.prompt_id
            else:
                logger().noop(
                    f"No user_prompt_{intention}.txt file found, using default."
                )
                chat_strategy_create.user_prompt_ids[intention] = (
                    chat_strategy_create.user_prompt_ids["default"]
                )
        strategy_create = convert_strategy_conf_create(chat_strategy_create)
        return self.create_strategy(strategy_create, user)

    def get_default_strategy(self) -> Strategy:
        return self.default_strategy

    def get_strategy_by_id(self, strategy_id: str) -> Optional[Strategy]:
        table_name = self._get_table_name()
        where_clause = f"WHERE {Strategy.FIELD_STRATEGY_ID} = '{strategy_id}'"
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
        )
        if result is None:
            return None
        return self._dict_to_strategy(result)

    def get_active_strategy_by_name(
        self, strategy_name: str, user: User
    ) -> Optional[Strategy]:
        if user is None:
            user = self.admin_user

        table_name = self._get_table_name()
        where_clause = (
            f"WHERE {Strategy.FIELD_USER_UUID} = '{user.user_uuid}' "
            f"AND {Strategy.FIELD_STRATEGY_NAME} = '{strategy_name}' "
            f"AND {Strategy.FIELD_STRATEGY_STATUS} = '{StrategyStatus.ACTIVE.value}'"
        )
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
        )
        if result is None:
            return None
        return self._dict_to_strategy(result)

    def set_strategy_status_by_id(
        self, strategy_id: str, status: StrategyStatus
    ) -> Strategy:
        table_name = self._get_table_name()
        column_list = [Strategy.FIELD_STRATEGY_STATUS, Strategy.FIELD_UPDATED_AT]
        value_list = [status.value, time_utils.current_datetime()]
        where_clause = f"WHERE {Strategy.FIELD_STRATEGY_ID} = '{strategy_id}'"
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_strategy_by_id(strategy_id)

    def list_active_strategies_for_user(self, user: User) -> List[Strategy]:
        if user is None:
            user = self.admin_user
            user_ids = [user.user_uuid]
        else:
            user_ids = [user.user_uuid, self.admin_user.user_uuid]

        results = [self.default_strategy]

        # Get all the active strategies for the user and the admin user
        table_name = self._get_table_name()
        where_clause = (
            f"WHERE {Strategy.FIELD_USER_UUID} IN ({', '.join([f'?' for _ in user_ids])}) "
            f"AND {Strategy.FIELD_STRATEGY_STATUS} = '{StrategyStatus.ACTIVE.value}'"
        )
        value_list = [user_id for user_id in user_ids]
        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        for rtn_dict in rtn_dicts:
            if (
                rtn_dict[Strategy.FIELD_STRATEGY_NAME]
                != self.default_strategy.strategy_name
            ):
                results.append(self._dict_to_strategy(rtn_dict))

        return results

    def _reset_for_test(self):
        """Reset the collection for testing."""
        if self.settings.COLLECTION_PROMPT.endswith("_test"):
            table_name = self._get_table_name()
            self.duckdb_client.delete_from_table(table_name=table_name)
            self._run_init()
