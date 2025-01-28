import os
import traceback
from pathlib import Path
from typing import ClassVar, Dict, List

from pydantic import BaseModel, Field

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.utils.obj_utils import ENV_VAR_PREFIX, add_env_var_constants
from leettools.core.schemas.user_settings import UserSettingsItem

# Absolute path to the directory containing the script
_script_dir = os.path.dirname(os.path.abspath(__file__))

# the default .env file is located under the project tree above src
_default_env_file = os.path.abspath(os.path.join(_script_dir, "../../.env"))


DOCX_EXT = ".docx"
HTML_EXT = ".html"
MD_EXT = ".md"
PDF_EXT = ".pdf"
PPTX_EXT = ".pptx"
TXT_EXT = ".txt"
XLSX_EXT = ".xlsx"
XLS_EXT = ".xls"


def supported_file_extensions() -> List[str]:
    return [DOCX_EXT, HTML_EXT, MD_EXT, PDF_EXT, PPTX_EXT, TXT_EXT, XLSX_EXT, XLS_EXT]


def supported_audio_file_extensions() -> List[str]:
    return ["mp3", "wav", "flac", "ogg", "m4a", "aac", "wma", "aiff", "alac"]


def supported_image_file_extensions() -> List[str]:
    return ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "svg"]


def supported_video_file_extensions() -> List[str]:
    return ["mp4", "avi", "flv", "wmv", "mov", "mkv", "webm", "m4v", "3gp", "3g2"]


def supported_media_file_extensions() -> List[str]:
    return (
        supported_audio_file_extensions()
        + supported_image_file_extensions()
        + supported_video_file_extensions()
    )


def is_media_file(file_ext: str) -> bool:
    return file_ext.strip(".") in supported_media_file_extensions()


def preset_store_types_for_tests() -> List[Dict[str, str]]:
    """
    Used in testing to preset the store types for different data store combos.
    """
    return [
        {
            "doc_store": "duckdb",
            "rdbms_store": "duckdb",
            "graph_store": "duckdb",
            "vector_store": "duckdb",
        },
    ]


@add_env_var_constants
class SystemSettings(BaseModel):
    """
    Global settings that should be set at the beginning of the system start.

    Most of the programs should read the settings only from this class.
    In testing environments, we can set the settings to a specific value.
    """

    # system settings that should not be changed unless the version of the system changes
    API_V1_STR: ClassVar[str] = "/api/v1"
    PROJECT_NAME: ClassVar[str] = "LeetTools"
    LEETAPI_PROJECT_NAME: ClassVar[str] = "LeetAPI"
    env_file: str = _default_env_file

    ##########################################################################
    #
    # Section 1: should not be changed after the system starts
    #            need to be checked for different deployment environments
    ##########################################################################

    DATA_ROOT: str = Field(None, description="The root directory for all the data")
    LOG_ROOT: str = Field(None, description="The root directory for all the logs")
    AUTH_ENABLED: bool = Field(
        False, description="Whether to enable the authentication"
    )

    #   Repo type for all the data storages unless overridden by the detailed settings
    #   For all the data manager xyz, the default implementation will be put under
    #      _impl/{repo_type}/xyz_{repo_type}.py
    #   To override, specify the full module name in the EDS_XYZ environment variable
    DOC_STORE_TYPE: str = Field("duckdb", description="The type of the document store")
    RDBMS_STORE_TYPE: str = Field("duckdb", description="The type of the RDBMS store")
    GRAPH_STORE_TYPE: str = Field("duckdb", description="The type of the graph store")
    VECTOR_STORE_TYPE: str = Field("duckdb", description="The type of the vector store")

    ##########################################################################
    #
    # Section 2: configuration values that may change the query results
    #
    ##########################################################################

    # 2.1.   Web Search
    WEB_RETRIEVER: str = Field(
        "google", description="The default web search retriever to use"
    )
    SEARCH_API_URL: str = Field(
        "https://svc.leettools.com:8098/customsearch/v1",
        description="The search API base URL",
    )
    FALLBACK_SCRAPER: str = Field(
        None,
        description=(
            "The fallback scraper to use if the default scraper fails, "
            "usually a more capable but more expensive scraper",
        ),
    )
    WEB_SITE_CRAWL_DEPTH: int = Field(
        3, description="The default depth of the web site crawl"
    )
    WEB_SITE_CRAWL_MAX_URLS: int = Field(
        100,
        description="The default max number of URLs to crawl for a single web site.",
    )
    SEARCH_MAX_RESULTS_FROM_RETRIEVER: int = Field(
        1000, description="The max number of search results from one retriever call"
    )
    RELEVANCE_THRESHOLD: int = Field(
        75, description="The relevance threshold for search results to be used."
    )

    # 2.2.   Document Pipeline

    # 2.2.1. Ingestion

    # 2.2.2. Conversion
    DEFAULT_PARSER: str = Field(
        "parser_docling", description="The default parser to use for conversion"
    )
    CONVERTER_API_URL: str = Field(
        "http://localhost:8001/api/v1/files/convert",
        description="The URL of the converter API if using a coverter service",
    )

    # 2.2.3. Chunking
    DEFAULT_CHUNKER: str = Field(
        "chunker_chonkie", description="The default chunker to use"
    )
    DEFAULT_CHUNK_SIZE: int = Field(
        512, description="The default chunk size for chunking"
    )
    DEFAULT_CHUNK_OVERLAP: int = Field(
        128, description="The default chunk overlap for chunking"
    )
    ENABLE_CONTEXTUAL_RETRIEVAL: bool = Field(
        False, description="Whether to enable contextual retrieval"
    )

    # 2.2.4. Embedding
    DEFAULT_SEGMENT_EMBEDDER_TYPE: str = Field(
        "simple", description="The default segment embedder type"
    )
    DEFAULT_SPARSE_EMBEDDER: str = Field(
        "sparse_embedder_splade", description="The default sparse embedder"
    )
    DEFAULT_DENSE_EMBEDDER: str = Field(
        "dense_embedder_openai", description="The default dense embedder"
    )
    DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME: str = Field(
        "all-MiniLM-L6-v2", description="The default dense embedding local model name"
    )
    DEFAULT_SPLADE_EMBEDDING_MODEL: str = Field(
        "naver/splade-cocondenser-selfdistil",
        description="The default splade embedding model",
    )

    # 2.3.   Retrieval

    # 2.3.1. Search
    DEFAULT_SEARCH_TOP_K: int = Field(
        20, description="The default top k search results to return"
    )

    # 2.3.2. Rerank settings
    DEFAULT_RERANK_STRATEGY: str = Field(
        "dummy", description="The default rerank strategy to use"
    )
    DEFAULT_RERANK_MODEL: str = Field(
        "rerank-english-v2.0", description="The default rerank model to use"
    )

    # 2.4.   LLM API call settings

    # 2.4.1. Default API providers
    DEFAULT_LLM_BASE_URL: str = Field(
        "https://api.openai.com/v1", description="The default base URL for LLM APIs"
    )
    DEFAULT_EMBEDDING_BASE_URL: str = Field(
        None,
        description=(
            "The default embedding base URL, default to the same as the LLM base URL",
        ),
    )
    RERANK_BASE_URL: str = Field(
        None, description="The default rerank base URL for the API"
    )

    # 2.4.2. Default Reference API parameters
    DEFAULT_CONTEXT_LIMIT: int = Field(
        16385, description="The default context limit for the API"
    )
    DEFAULT_TEMPERATURE: float = Field(
        0.0, description="The default temperature for the LLM API reference call"
    )
    DEFAULT_MAX_TOKENS: int = Field(
        -1,
        description=(
            "The default max tokens for the LLM API reference call, "
            "if -1, it will be the default context limit",
        ),
    )

    # 2.4.3. Default models
    DEFAULT_INFERENCE_MODEL: str = Field(
        "gpt-4o-mini", description="The default inference model to use"
    )
    DEFAULT_SUMMARIZING_MODEL: str = Field(
        None, description="The default summarizing model to use"
    )
    DEFAULT_PLANNING_MODEL: str = Field(
        None, description="The default planning model to use"
    )
    DEFAULT_WRITING_MODEL: str = Field(
        None, description="The default writing model to use"
    )
    DEFAULT_EMBEDDING_MODEL: str = Field(
        "text-embedding-3-small",
        description="The default embedding model to use",
    )
    EMBEDDING_MODEL_DIMENSION: int = Field(
        1536, description="The default embedding model dimension"
    )

    ##########################################################################
    #
    # Section 3: configurations that probably need to change for each deployment
    #            they do not change the results, but need to be set up correctly
    #
    ##########################################################################

    # 3.1.   General settings
    DEFAULT_LANGUAGE: str = Field(
        "en", description="The default language for the system"
    )
    SHARE_SAMPLES_FROM_USERS: str = Field(
        "admin, saturn, leettools",
        description="The users to share samples from, separated by comma.",
    )

    # 3.2.   Path settings
    CODE_ROOT_PATH: Path = Field(
        Path(_script_dir).parent, description="The root path of the code"
    )
    EXTENSION_PATH: Path = Field(
        Path(_script_dir).parent / "extensions", description="The extension path"
    )
    DOCSINK_LOCAL_DIR: str = Field(
        None, description="The directory to store the docsink files"
    )
    DOCUMENT_LOCAL_DIR: str = Field(
        None, description="The directory to store the document files"
    )
    STRATEGY_PATH: str = Field(
        None, description="The directory to store the strategy files"
    )

    # 3.3.   API Keys
    LLM_API_KEY: str = Field(
        None,
        description=(
            "The default LLM API key for the LLM Reference API. It is "
            "possible to use a different compatible API provider and set their "
            "API key here."
        ),
    )
    RERANK_API_KEY: str = Field(
        None, description="The default rerank API key for the rerank API"
    )
    BING_SEARCH_API_KEY: str = Field(
        None, description="The default Bing search API key"
    )
    EMBEDDING_API_KEY: str = Field(
        None,
        description=(
            "The default embedding API key for the embedding API. If not set, the "
            "LLM API key will be used.",
        ),
    )
    OPENAI_UTILS_ENABLED: bool = Field(
        False,
        description=(
            "Whether to enable the OpenAI utils in the document pipeline."
            "Right now it is experimental."
        ),
    )

    # 3.4.   Bookkeeper and Subscription related settings
    STRIPE_SECRET_KEY: str = Field(
        None, description="The default Stripe secret key for the payment"
    )
    STRIPE_PAYMENT_LINK: str = Field(
        None, description="The default Stripe payment link for the payment"
    )
    STRIPE_ENDPOINT_SECRET: str = Field(
        None, description="The default Stripe endpoint secret for the payment"
    )
    DEFAULT_BOOKKEEPER: str = Field(
        "bookkeeper_stripe", description="The default bookkeeper for the payment"
    )
    DEFAULT_TOKEN_CONVERTER: str = Field(
        "token_converter_basic", description="The default token converter"
    )
    ##########################################################################
    #
    # Section 4: configurations do not change the results
    #            should mostly leave as is unless there is a specific reason to change
    #
    ##########################################################################

    ## 4.1   Default values

    DEFAULT_FLOW_TYPE: str = Field(
        "answer", description="The default flow type for the system"
    )

    API_SERVICE_HOST: str = Field(
        "127.0.0.1", description="The default API service host for the system"
    )
    API_SERVICE_PORT: int = Field(
        8000, description="The default API service port for the system"
    )

    DEFAULT_DENSE_EMBEDDING_SERVICE_HOST: str = Field(
        "127.0.0.1",
        description=(
            "The default local dense embedding service host if we start a local "
            "embedding service",
        ),
    )
    DEFAULT_DENSE_EMBEDDING_SERVICE_PORT: int = Field(
        8001,
        description=(
            "The default local dense embedding service port if we start a local "
            "embedding service",
        ),
    )

    DEFAULT_DENSE_EMBEDDING_SERVICE_ENDPOINT: str = Field(
        "http://127.0.0.1:8001/api/v1/embed",
        description="The default dense embedding service endpoint",
    )

    DEFAULT_EMAILER: str = Field(
        "emailer_mailgun", description="The default emailer to use"
    )

    INIT_STRATEGY_STORE: bool = Field(
        True, description="Whether to initialize the strategy store at the beginning."
    )

    ## 4.2   Pipeline related setting
    ##       System related settings that can change during runtime
    DOCSOURCE_RETRY_RANGE_IN_HOURS: int = Field(
        24,
        description=(
            "The default retry range in hours for the docsources. "
            "The scheduler will ignore data sources older than this range.",
        ),
    )
    scheduler_default_number_worker: int = Field(
        8, description="The default number of worker threads for the scheduler"
    )
    scheduler_base_delay_in_seconds: int = Field(
        10,
        description=(
            "The default base delay in seconds for the exponential backup "
            "for failed tasks in scheduler."
        ),
    )
    scheduler_max_delay_in_seconds: int = Field(
        60,
        description=(
            "The default max delay in seconds for the exponential backup "
            "for failed tasks in scheduler."
        ),
    )
    scheduler_max_retries: int = Field(
        3, description="The default max retries for a task in the scheduler."
    )

    ## 4.3.  Name of kb and collections
    DEFAULT_ORG_NAME: str = Field(
        "org-default", description="The default organization name for the system"
    )
    DEFAULT_ORG_ID: str = Field(
        "org-default-id", description="The default organization ID for the system"
    )
    DEFAULT_KNOWLEDGEBASE_NAME: str = Field(
        "kb-default", description="The default knowledge base name for the system"
    )
    DB_COMMOM: str = Field(
        "common", description="The default common database for the system"
    )
    DB_USAGE: str = Field(
        "usage", description="The default usage database for the system"
    )
    DB_TASKS: str = Field(
        "tasks", description="The default tasks database for the system"
    )

    COLLECTION_PROMPT: str = Field(
        "prompts", description="The default prompt collection for the system"
    )
    COLLECTION_STRATEGY: str = Field(
        "strategies", description="The default strategy collection for the system"
    )
    COLLECTION_INTENTIONS: str = Field(
        "intentions", description="The default intentions collection for the system"
    )
    COLLECTION_USER_SETTINGS: str = Field(
        "user_settings",
        description="The default user settings collection for the system",
    )
    COLLECTION_API_PROVIDERS: str = Field(
        "api_providers",
        description="The default API providers collection for the system",
    )
    COLLECTION_CHAT_HISTORY: str = Field(
        "chat_history", description="The default chat history collection for the system"
    )
    COLLECTION_TASKS: str = Field(
        "tasks", description="The default tasks collection for the system"
    )
    COLLECTION_JOBS: str = Field(
        "jobs", description="The default jobs collection for the system"
    )
    COLLECTION_KB: str = Field(
        "kb", description="The default knowledge base collection for the system"
    )
    COLLECTION_KB_METADATA: str = Field(
        "kb_metadata", description="The default knowledge base metadata collection"
    )
    COLLECTION_ORG: str = Field(
        "orgs", description="The default organization collection for the system"
    )
    COLLECTION_USERS: str = Field(
        "users", description="The default users collection for the system"
    )

    ## 4.3   Bookkeeper and subscription related settings
    COLLECTION_LOCKS: str = Field(
        "locks", description="The default locks collection for the system"
    )
    BALANCE_LOCK_NAME: str = Field(
        "balance_lock", description="The default balance lock name for the system"
    )
    COLLECTION_BALANCE_CHANGE: str = Field(
        "balance_change",
        description="The default balance change collection for the system",
    )

    ##########################################################################
    #
    # Section 5: Settings for different pluggable components
    #
    ##########################################################################

    # 5.1.   DB Settings
    DUCKDB_PATH: str = Field(
        None, description="The default path for the DuckDB database"
    )
    DUCKDB_FILE: str = Field(
        "duckdb.db", description="The default file for the DuckDB database"
    )

    def initialize(
        self, env_file_path: str = _default_env_file, override: bool = False
    ) -> "SystemSettings":
        """
        Initialize the settings with default values set in the env file. If the override
        flag is set to True, the environment variables will be overwritten by the values
        set in the env file. We usually set override to true only in the testing environment.
        """
        # system settings that should be set at the begining of the system start
        #
        logger().debug("Initializing settings with default values.")
        logger().debug(f"Loading environment variables from .env file: {env_file_path}")
        self.env_file = env_file_path

        # load the environment variables from the .env file
        # if an env variable is already set in the system, it will not be overwritten
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_file_path, override=override)

        leet_home = os.environ.get("LEET_HOME", None)
        if leet_home is None or leet_home == "":
            home_dir = Path.home()
            leet_home = str(home_dir / "leettools")
            logger().debug(
                f"The LEET_HOME env var is not set. Using {leet_home} as default. "
            )

        # create the leet_home directory if it does not exist
        if not os.path.exists(leet_home):
            logger().info(f"Creating the LEET_HOME directory: {leet_home}")
            os.makedirs(leet_home)

        eds_data_root = os.environ.get(f"{ENV_VAR_PREFIX}DATA_ROOT", None)
        eds_log_root = os.environ.get(f"{ENV_VAR_PREFIX}LOG_ROOT", None)
        if not eds_data_root:
            os.environ[f"{ENV_VAR_PREFIX}DATA_ROOT"] = f"{leet_home}/data"
            self.DATA_ROOT = f"{leet_home}/data"
        else:
            self.DATA_ROOT = eds_data_root

        if not eds_log_root:
            os.environ[f"{ENV_VAR_PREFIX}LOG_ROOT"] = f"{leet_home}/logs"
            self.LOG_ROOT = f"{leet_home}/logs"
        else:
            self.LOG_ROOT = eds_log_root

        for field_name in self.model_fields.keys():
            if field_name in self.__class_vars__:
                continue

            env_var_name = f"{ENV_VAR_PREFIX}{field_name.upper()}"
            env_var = os.environ.get(env_var_name, None)

            if env_var is not None:
                logger().debug(
                    f"Setting from environment variable: {field_name}={env_var}"
                )
                setattr(self, field_name, env_var)

        # set derived values that have not been set by env variables

        if self.EXTENSION_PATH is None:
            self.EXTENSION_PATH = Path(self.CODE_ROOT_PATH / "extensions")
        if self.DOCSINK_LOCAL_DIR is None:
            self.DOCSINK_LOCAL_DIR = self.DATA_ROOT + "/docsink"
        if self.DOCUMENT_LOCAL_DIR is None:
            self.DOCUMENT_LOCAL_DIR = self.DATA_ROOT + "/document"
        if self.STRATEGY_PATH is None:
            self.STRATEGY_PATH = self.DATA_ROOT + "/strategy"

        if self.DUCKDB_PATH is None:
            self.DUCKDB_PATH = self.DATA_ROOT + "/duckdb"

        self.check_required_vars()

        logger().debug("Finished initializing settings.")
        return self

    def get_user_configurable_settings(self) -> Dict[str, UserSettingsItem]:
        """
        Get the user settings that can be configured by the user.
        """
        return {
            "LLM_API_KEY": UserSettingsItem(
                section="RAG",
                name="LLM_API_KEY",
                description="LLM API Key used in the inference process.",
                default_value=None,
                value_type="str",
            ),
            "LLM_BASE_URL": UserSettingsItem(
                section="RAG",
                name="LLM_BASE_URL",
                description="LLM Base URL used in the inference process.",
                default_value=self.DEFAULT_LLM_BASE_URL,
                value_type="str",
            ),
            "DEFAULT_INFERENCE_MODEL": UserSettingsItem(
                section="RAG",
                name="DEFAULT_INFERENCE_MODEL",
                description="Default inference Model used in the inference process.",
                default_value=self.DEFAULT_INFERENCE_MODEL,
                value_type="str",
            ),
            "EMBEDDING_API_KEY": UserSettingsItem(
                section="RAG",
                name="EMBEDDING_API_KEY",
                description="API Key used for the embedder.",
                default_value=self.EMBEDDING_API_KEY,
                value_type="str",
            ),
            "EMBEDDING_BASE_URL": UserSettingsItem(
                section="RAG",
                name="EMBEDDING_BASE_URL",
                description="Base URL for the the embedder service.",
                default_value=self.DEFAULT_EMBEDDING_BASE_URL,
                value_type="str",
            ),
            "RERANK_API_KEY": UserSettingsItem(
                section="RAG",
                name="RERANK_API_KEY",
                description="API Key used in the reranking process.",
                default_value=None,
                value_type="str",
            ),
            "RERANK_BASE_URL": UserSettingsItem(
                section="RAG",
                name="RERANK_BASE_URL",
                description="Base url used in the reranking process.",
                default_value=None,
                value_type="str",
            ),
            "GOOGLE_API_KEY": UserSettingsItem(
                section="RAG",
                name="GOOGLE_API_KEY",
                description="Google API Key used in the search process.",
                default_value=None,
                value_type="str",
            ),
            "GOOGLE_CX_KEY": UserSettingsItem(
                section="RAG",
                name="GOOGLE_CX_KEY",
                description="Google custom search Key used in the search process.",
                default_value=None,
                value_type="str",
            ),
            "GOOGLE_PATENT_CX_KEY": UserSettingsItem(
                section="RAG",
                name="GOOGLE_PATENT_CX_KEY",
                description="Google custom search Key for patent used in the search process.",
                default_value=None,
                value_type="str",
            ),
            "TAVILY_API_KEY": UserSettingsItem(
                section="RAG",
                name="TAVILY_API_KEY",
                description="Tavily API Key used in the search process.",
                default_value=None,
                value_type="str",
            ),
        }

    def check_required_vars(self) -> None:
        err_msgs = []
        if not self.DATA_ROOT:
            err_msgs.append(
                "Required variable DATA_ROOT is not set. "
                "Set the environment variable EDS_DATA_ROOT or LEET_HOME."
            )

        if not self.LOG_ROOT:
            err_msgs.append(
                "Required variable LOG_ROOT is not set. "
                "Set the environment variable EDS_LOG_ROOT or LEET_HOME."
            )

        if not self.LLM_API_KEY:
            logger().debug("No LLM_API_KEY is set. Using dummy-api-key as default.")
            self.LLM_API_KEY = "dummy-api-key"

        if err_msgs:
            raise exceptions.ParametersValidationException(err_msgs)

    def using_default_env(self) -> bool:
        return self.env_file == _default_env_file

    def __repr__(self) -> str:
        return f"SystemSettings({self.__dict__})"
