from leettools.cli import cli_utils
from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.str_embedder.dense_embedder import (
    AbstractDenseEmbedder,
    create_dense_embedder_for_kb,
    get_dense_embedder_class,
)


def test_embedder_is_compatible(tmp_path):

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

    org_01, kb_01, user_01 = cli_utils.setup_org_kb_user(
        context=context, org_name=org.name, kb_name=kb.name, username=user.username
    )

    embedder_01: AbstractDenseEmbedder = create_dense_embedder_for_kb(
        context=context, org=org, kb=kb_01, user=user
    )

    assert embedder_01.is_compatible(embedder_01)

    dense_embedder_class = get_dense_embedder_class(None, context.settings)
    default_embedder: AbstractDenseEmbedder = dense_embedder_class(
        context=context,
        org=org,
        kb=kb,
        user=user,
    )

    assert embedder_01.is_compatible(default_embedder)
    assert default_embedder.is_compatible(embedder_01)

    if dense_embedder_class.__name__ == "DenseEmbedderOpenAI":
        incompatible_embedder_name = "dense_embedder_sentence_transformer"
    elif dense_embedder_class.__name__ == "DenseEmbedderSentenceTransformer":
        incompatible_embedder_name = "dense_embedder_openai"
    else:
        logger().warning(
            f"Unknown default dense embedder class: {dense_embedder_class.__name__}"
        )
        return

    incompatible_embedder_class = get_dense_embedder_class(
        incompatible_embedder_name, context.settings
    )
    incompatible_embedder: AbstractDenseEmbedder = incompatible_embedder_class(
        context=context,
    )

    assert embedder_01.is_compatible(incompatible_embedder) is False
    assert default_embedder.is_compatible(incompatible_embedder) is False
