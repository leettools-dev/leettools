from typing import Any, Dict, Optional

from leettools.common.exceptions import ConfigValueException
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.context_manager import Context
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
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ) -> None:

        self.org = org
        self.kb = kb
        self.user = user
        self.context = context
        self.usage_store = context.get_usage_store()
        settings = context.settings

        if kb is None:
            self.model_name = settings.DEFAULT_EMBEDDING_MODEL
            self.embedding_model_dimension = settings.EMBEDDING_MODEL_DIMENSION
        else:
            params = kb.dense_embedder_params
            if params is None or DENSE_EMBED_PARAM_MODEL not in params:
                self.model_name = settings.DEFAULT_EMBEDDING_MODEL
                self.embedding_model_dimension = settings.EMBEDDING_MODEL_DIMENSION
            else:
                self.model_name = params[DENSE_EMBED_PARAM_MODEL]
                if (
                    DENSE_EMBED_PARAM_DIM not in params
                    or params[DENSE_EMBED_PARAM_MODEL] is None
                ):
                    raise ConfigValueException(
                        DENSE_EMBED_PARAM_DIM, "Embedding model dim not specified."
                    )
                self.embedding_model_dimension = params[DENSE_EMBED_PARAM_DIM]

        if self.user is not None:
            user = self.user
        else:
            user_store = self.context.get_user_store()
            if self.kb is None:
                logger().debug(f"No KB specified. Using admin user.")
                user = user_store.get_user_by_name(User.ADMIN_USERNAME)
            else:
                if self.kb.user_uuid is None:
                    logger().warning(
                        f"KB {self.kb.name} has no user_uuid specified. Using admin user."
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

    def embed(self, embed_requests: DenseEmbeddingRequest) -> DenseEmbeddings:

        response = None
        start_timestamp_in_ms = time_utils.cur_timestamp_in_ms()
        try:
            response = self.openai.embeddings.create(
                input=embed_requests.sentences, model=self.model_name
            )
            rtn_list = []
            for i in range(len(response.data)):
                rtn_list.append(response.data[i].embedding)
        except Exception as e:
            logger().error(f"Embedding operation failed: {e}")
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
                api_provider=self.api_provider_config.api_provider,
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

    def get_model_name(self) -> str:
        return self.model_name

    def get_dimension(self) -> int:
        return self.embedding_model_dimension

    @classmethod
    def get_default_params(cls, settings: SystemSettings) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        params[DENSE_EMBED_PARAM_MODEL] = settings.DEFAULT_EMBEDDING_MODEL
        params[DENSE_EMBED_PARAM_DIM] = settings.EMBEDDING_MODEL_DIMENSION
        return params
