from typing import Any, Dict, Tuple

from openai import OpenAI

from leettools.common.exceptions import ConfigValueException
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.context_manager import Context
from leettools.core.schemas.api_provider_config import APIProviderConfig
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.api_caller.api_utils import get_openai_embedder_client_for_user
from leettools.eds.str_embedder.dense_embedder import (
    DENSE_EMBED_PARAM_DIM,
    DENSE_EMBED_PARAM_MODEL,
    AbstractDenseEmbedder,
)
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
    DenseEmbeddings,
)
from leettools.eds.usage.schemas.usage_api_call import (
    API_CALL_ENDPOINT_EMBED,
    UsageAPICallCreate,
)
from leettools.settings import SystemSettings


class DenseEmbedderOpenAI(AbstractDenseEmbedder):

    def __init__(
        self, org: Org, kb: KnowledgeBase, user: User, context: Context
    ) -> None:

        self.org = org
        self.kb = kb
        self.user = user
        self.context = context
        self.usage_store = context.get_usage_store()

        params = kb.dense_embedder_params
        if params is None or DENSE_EMBED_PARAM_MODEL not in params:
            settings = context.settings
            self.model_name = settings.DEFAULT_EMBEDDING_OPENAI_MODEL
            self.OPENAI_EMBEDDING_MODEL_DIMENSION = (
                settings.EMBEDDING_OPENAI_MODEL_DIMENSION
            )
        else:
            self.model_name = params[DENSE_EMBED_PARAM_MODEL]
            if (
                DENSE_EMBED_PARAM_DIM not in params
                or params[DENSE_EMBED_PARAM_MODEL] is None
            ):
                raise ConfigValueException(
                    DENSE_EMBED_PARAM_DIM, "OpenAI embedding model dim not specified."
                )
            self.OPENAI_EMBEDDING_MODEL_DIMENSION = params[DENSE_EMBED_PARAM_DIM]
        self.openai: OpenAI = None

    def _get_openai_embedder_client(self) -> Tuple[APIProviderConfig, OpenAI]:
        if self.openai is not None:
            return self.api_provider_config, self.openai

        user_store = self.context.get_user_store()
        if self.user is not None:
            user = self.user
        else:
            if self.kb.user_uuid is None:
                logger().warning(
                    f"KB {self.kb.name} has no user_uuid. Using admin user."
                )
                user = user_store.get_user_by_name(User.ADMIN_USERNAME)
            else:
                user = user_store.get_user_by_uuid(user_uuid=self.kb.user_uuid)
                if user is None:
                    logger().warning(
                        f"KB {self.kb.name} has invalid user_uuid. Using admin user."
                    )
                    user = user_store.get_user_by_name(User.ADMIN_USERNAME)

        self.api_provider_config, self.openai = get_openai_embedder_client_for_user(
            context=self.context, user=user, api_provider_config=None
        )
        return self.api_provider_config, self.openai

    def embed(self, embed_requests: DenseEmbeddingRequest) -> DenseEmbeddings:
        api_provider_config, openai = self._get_openai_embedder_client()

        response = None
        start_timestamp_in_ms = time_utils.cur_timestamp_in_ms()
        try:
            response = openai.embeddings.create(
                input=embed_requests.sentences, model=self.model_name
            )
            rtn_list = []
            for i in range(len(response.data)):
                rtn_list.append(response.data[i].embedding)
        except Exception as e:
            logger().error(f"OpenAI embedding failed: {e}")
            raise e
        finally:
            end_timestamp_in_ms = time_utils.cur_timestamp_in_ms()
            if response is not None:
                success = True
                total_token_count = response.usage.total_tokens
                input_token_count = response.usage.prompt_tokens
                output_token_count = total_token_count - input_token_count
            else:
                success = False
                total_token_count = 0
                input_token_count = -1
                output_token_count = -1

            usage_api_call = UsageAPICallCreate(
                user_uuid=self.user.user_uuid,
                api_provider=api_provider_config.api_provider,
                target_model_name=self.model_name,
                endpoint=API_CALL_ENDPOINT_EMBED,
                success=success,
                total_token_count=total_token_count,
                start_timestamp_in_ms=start_timestamp_in_ms,
                end_timestamp_in_ms=end_timestamp_in_ms,
                is_batch=False,
                system_prompt="",
                user_prompt="\n".join(embed_requests.sentences),
                call_target="embed",
                input_token_count=input_token_count,
                output_token_count=output_token_count,
            )
            self.usage_store.record_api_call(usage_api_call)
        return DenseEmbeddings(dense_embeddings=rtn_list)

    def get_dimension(self) -> int:
        return self.OPENAI_EMBEDDING_MODEL_DIMENSION

    @classmethod
    def get_default_params(cls, settings: SystemSettings) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        params[DENSE_EMBED_PARAM_MODEL] = settings.DEFAULT_EMBEDDING_OPENAI_MODEL
        params[DENSE_EMBED_PARAM_DIM] = settings.EMBEDDING_OPENAI_MODEL_DIMENSION
        return params
