import os
from http import HTTPStatus
from typing import Any, Dict, Optional

import dashscope

from leettools.common.exceptions import ConfigValueException
from leettools.common.logging import logger
from leettools.common.utils import config_utils, time_utils
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
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

EMBEDDER_MODEL_MAPPNG = {
    "text-embedding-v1": dashscope.TextEmbedding.Models.text_embedding_v1,
    "text-embedding-v2": dashscope.TextEmbedding.Models.text_embedding_v2,
}


class DenseEmbedderQwen(AbstractDenseEmbedder):

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

        self.QWEN_API_PROVIDER_NAME = os.environ.get(
            "QWEN_API_PROVIDER_NAME", "aliyuncs"
        )
        self.DASHSCORE_API_KEY = os.environ.get("DEFAULT_DASHSCOPE_API_KEY")

        if kb is None:
            self.model_name = os.environ.get(
                "DEFAULT_EMBEDDING_QWEN_MODEL", "text-embedding-v2"
            )
            self.QWEN_EMBEDDING_MODEL_DIMENSION = 1536
        else:
            params = kb.dense_embedder_params
            if params is None or DENSE_EMBED_PARAM_MODEL not in params:
                self.model_name = os.environ.get(
                    "DEFAULT_EMBEDDING_QWEN_MODEL", "text-embedding-v2"
                )
                self.QWEN_EMBEDDING_MODEL_DIMENSION = 1536
            else:
                self.model_name = params[DENSE_EMBED_PARAM_MODEL]
                if (
                    DENSE_EMBED_PARAM_DIM not in params
                    or params[DENSE_EMBED_PARAM_MODEL] is None
                ):
                    raise ConfigValueException(
                        DENSE_EMBED_PARAM_DIM, "Qwen embedding model dim not specified."
                    )
                self.QWEN_EMBEDDING_MODEL_DIMENSION = int(params[DENSE_EMBED_PARAM_DIM])

    def embed(self, embed_requests: DenseEmbeddingRequest) -> DenseEmbeddings:
        response = None
        start_timestamp_in_ms = time_utils.cur_timestamp_in_ms()
        try:
            rtn_list = []
            for sentence in embed_requests.sentences:
                resp = dashscope.TextEmbedding.call(
                    model=EMBEDDER_MODEL_MAPPNG[self.model_name],
                    api_key=self.DASHSCORE_API_KEY,
                    input=sentence,
                )
                if resp.status_code == HTTPStatus.OK:
                    rtn_list.append(resp["output"]["embeddings"][0]["embedding"])
                else:
                    logger().error(f"Qwen embedding failed: {resp}")
                    raise Exception(f"Qwen embedding failed: {resp}")
        except Exception as e:
            logger().error(f"Qwen embedding failed: {e}")
            raise e
        finally:
            end_timestamp_in_ms = time_utils.cur_timestamp_in_ms()
            if resp.status_code == HTTPStatus.OK:
                success = True
                total_token_count = resp["usage"]["total_tokens"]
                input_token_count = total_token_count
                output_token_count = total_token_count - input_token_count
            else:
                success = False
                total_token_count = 0
                input_token_count = -1
                output_token_count = -1

            usage_api_call = UsageAPICallCreate(
                user_uuid=self.user.user_uuid,
                api_provider=self.QWEN_API_PROVIDER_NAME,
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
        return self.QWEN_EMBEDDING_MODEL_DIMENSION

    @classmethod
    def get_default_params(cls, context: Context, user: User) -> Dict[str, Any]:
        if user is None:
            user = User.get_admin_user()
        user_settings_store = context.get_user_settings_store()
        user_settings = user_settings_store.get_settings_for_user(user)
        params: Dict[str, Any] = {}

        if context.is_svc:
            params[DENSE_EMBED_PARAM_MODEL] = user_settings.get_value(
                key="DEFAULT_EMBEDDING_QWEN_MODEL",
                default_value=os.environ.get(
                    "DEFAULT_EMBEDDING_QWEN_MODEL", "text-embedding-v2"
                ),
            )
            params[DENSE_EMBED_PARAM_DIM] = user_settings.get_value(
                key="EMBEDDING_QWEN_MODEL_DIMENSION",
                default_value=os.environ.get("EMBEDDING_QWEN_MODEL_DIMENSION", 1536),
            )
        else:
            value = os.environ.get("DEFAULT_EMBEDDING_QWEN_MODEL", None)
            if value is None or value == "":
                value = user_settings.get_value(
                    key="DEFAULT_EMBEDDING_QWEN_MODEL",
                    default_value="text-embedding-v2",
                )
            params[DENSE_EMBED_PARAM_MODEL] = value

            value = os.environ.get("EMBEDDING_QWEN_MODEL_DIMENSION", None)
            if value is None or value == "":
                value = user_settings.get_value(
                    key="EMBEDDING_QWEN_MODEL_DIMENSION", default_value=1536
                )
            params[DENSE_EMBED_PARAM_DIM] = value
        return params
