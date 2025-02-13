import threading
from enum import Enum
from typing import ClassVar, Optional

from leettools.common.singleton_meta import SingletonMeta
from leettools.core.auth.authorizer import AbstractAuthorizer, create_authorizer
from leettools.core.config.config_manager import ConfigManager
from leettools.core.knowledgebase.kb_manager import AbstractKBManager, create_kb_manager
from leettools.core.org.org_manager import AbstractOrgManager, create_org_manager
from leettools.core.repo.repo_manager import RepoManager
from leettools.core.strategy.intention_store import (
    AbstractIntentionStore,
    create_intention_store,
)
from leettools.core.strategy.prompt_store import AbstractPromptStore, create_promptstore
from leettools.core.strategy.strategy_store import (
    AbstractStrategyStore,
    create_strategy_store,
)
from leettools.core.user.user_settings_store import (
    AbstractUserSettingsStore,
    create_user_settings_store,
)
from leettools.core.user.user_store import AbstractUserStore, create_user_store
from leettools.eds.scheduler.task.task_manager import TaskManager
from leettools.eds.usage.usage_store import AbstractUsageStore, create_usage_store
from leettools.settings import SystemSettings


class SingletonMetaContext(SingletonMeta):
    _lock: threading.Lock = threading.Lock()


class ContextStatus(str, Enum):
    RUNNING = "running"
    CLOSED = "closed"


class Context:

    EDS_CLI_CONTEXT_PREFIX: ClassVar[str] = "eds_cli"

    def __init__(self, settings: SystemSettings):
        self.name = "default_context"

        self.is_svc = True
        self.is_test = False
        self.scheduler_is_running = False

        self.settings = settings
        self._config_manager = ConfigManager()
        # Used in tests to reset the context
        self.initial_settings = settings.model_copy()

        self._org_manager: Optional[AbstractOrgManager] = None
        self._user_store: Optional[AbstractUserStore] = None
        self._kb_manager: Optional[AbstractKBManager] = None

        self._repo_manager: Optional[RepoManager] = None

        self._prompt_store: Optional[AbstractPromptStore] = None
        self._intention_store: Optional[AbstractIntentionStore] = None
        self._strategy_store: Optional[AbstractStrategyStore] = None

        self._usage_store: Optional[AbstractUsageStore] = None
        self._user_settings_store: Optional[AbstractUserSettingsStore] = None
        self._authorizer: Optional[AbstractAuthorizer] = None

        self._task_manager: Optional[TaskManager] = None

        # now the context is ready to be used
        self.status = ContextStatus.RUNNING
        self.lock = threading.Lock()

        # the splade encoder library reports error the first time it loads the lib
        # try:
        #     from transformers import AutoModelForMaskedLM, AutoTokenizer
        # except ImportError as e:
        #     print(f"transformers is not installed. {e}")
        # except Exception as e:
        #     pass

    def is_cli(self) -> bool:
        return self.name.startswith(self.EDS_CLI_CONTEXT_PREFIX)

    def get_config_manager(self) -> ConfigManager:
        return self._config_manager

    def get_authorizer(self):
        with self.lock:
            if self._user_store is None:
                self._user_store = create_user_store(self.settings)
            if self._authorizer is None:
                self._authorizer = create_authorizer(self.settings, self._user_store)
            return self._authorizer

    def get_prompt_store(self) -> AbstractPromptStore:
        with self.lock:
            if self._prompt_store is None:
                self._prompt_store = create_promptstore(self.settings)
            return self._prompt_store

    def get_intention_store(self) -> AbstractIntentionStore:
        with self.lock:
            if self._intention_store is None:
                self._intention_store = create_intention_store(self.settings)
            return self._intention_store

    def get_strategy_store(self) -> AbstractStrategyStore:
        with self.lock:
            if self._user_store is None:
                self._user_store = create_user_store(self.settings)
            if self._prompt_store is None:
                self._prompt_store = create_promptstore(self.settings)
            if self._intention_store is None:
                self._intention_store = create_intention_store(self.settings)
            if self._strategy_store is None:
                self._strategy_store = create_strategy_store(
                    settings=self.settings,
                    prompt_store=self._prompt_store,
                    intention_store=self._intention_store,
                    user_store=self._user_store,
                    run_init=self.settings.INIT_STRATEGY_STORE,
                )
            return self._strategy_store

    def get_user_settings_store(self) -> AbstractUserSettingsStore:
        with self.lock:
            if self._user_settings_store is None:
                self._user_settings_store = create_user_settings_store(
                    settings=self.settings
                )
            return self._user_settings_store

    def get_repo_manager(self) -> RepoManager:
        with self.lock:
            if self._repo_manager is None:
                self._repo_manager = RepoManager(self.settings)
            return self._repo_manager

    def get_org_manager(self) -> AbstractOrgManager:
        with self.lock:
            if self._org_manager is None:
                self._org_manager = create_org_manager(self.settings)
            return self._org_manager

    def get_user_store(self) -> AbstractUserStore:
        with self.lock:
            if self._user_store is None:
                self._user_store = create_user_store(self.settings)

            return self._user_store

    def get_kb_manager(self) -> AbstractKBManager:
        with self.lock:
            if self._kb_manager is None:
                self._kb_manager = create_kb_manager(self.settings)
            return self._kb_manager

    def get_usage_store(self) -> AbstractUsageStore:
        with self.lock:
            if self._user_store is None:
                self._user_store = create_user_store(self.settings)
            if self._usage_store is None:
                self._usage_store = create_usage_store(self.settings, self._user_store)
            return self._usage_store

    def get_task_manager(self) -> TaskManager:
        with self.lock:
            if self._task_manager is None:
                self._task_manager = TaskManager(self.settings)
            return self._task_manager

    def reset(self, is_test: bool = False, new_env_file: str = None):

        self.is_test = is_test
        settings = self.initial_settings.model_copy()

        if new_env_file is not None:
            settings = SystemSettings().initialize(
                env_file_path=new_env_file, override=True
            )

        if self.is_test:
            if not settings.DB_COMMOM.endswith("_test"):
                settings.DB_COMMOM = settings.DB_COMMOM + "_test"
            if not settings.DB_USAGE.endswith("_test"):
                settings.DB_USAGE = settings.DB_USAGE + "_test"
            if not settings.DB_TASKS.endswith("_test"):
                settings.DB_TASKS = settings.DB_TASKS + "_test"
            if not settings.DATA_ROOT.endswith("_test"):
                settings.DATA_ROOT = settings.DATA_ROOT + "_test"
            if not settings.LOG_ROOT.endswith("_test"):
                settings.LOG_ROOT = settings.LOG_ROOT + "_test"
            if not settings.COLLECTION_STRATEGY.endswith("_test"):
                settings.COLLECTION_STRATEGY = settings.COLLECTION_STRATEGY + "_test"
            if not settings.COLLECTION_INTENTIONS.endswith("_test"):
                settings.COLLECTION_INTENTIONS = (
                    settings.COLLECTION_INTENTIONS + "_test"
                )
            if not settings.COLLECTION_PROMPT.endswith("_test"):
                settings.COLLECTION_PROMPT = settings.COLLECTION_PROMPT + "_test"
            if not settings.DUCKDB_FILE.endswith("_test.db"):
                settings.DUCKDB_FILE = settings.DUCKDB_FILE.replace(".db", "_test.db")
        self._reset_with_new_settings(settings)

    def _reset_with_new_settings(self, settings: SystemSettings):
        self.settings = settings

        # TODO: reset all the dependencies used
        self._repo_manager = None
        self._task_manager = None
        self._embedder = None
        self._kb_manager = None
        self._org_manager = None
        self._user_store = None

        self._prompt_store = None
        self._intention_store = None
        self._strategy_store = None
        self._usage_store = None
        self._user_settings_store = None

        # now the context is ready to be used
        self.status = ContextStatus.RUNNING


class ContextManager(metaclass=SingletonMetaContext):
    def __init__(self, settings: Optional[SystemSettings] = None):
        if not hasattr(
            self, "initialized"
        ):  # This ensures __init__ is only called once
            self.initialized = True
            if settings is None:
                settings = SystemSettings().initialize()
            self._context = Context(settings)  # type: Context

    def get_context(self) -> Context:
        return self._context
