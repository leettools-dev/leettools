from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger, logger
from leettools.context_manager import Context
from leettools.core.consts.segment_embedder_type import SegmentEmbedderType
from leettools.core.schemas.knowledgebase import KBCreate
from leettools.core.schemas.user import User
from leettools.eds.str_embedder.dense_embedder import (
    AbstractDenseEmbedder,
    get_dense_embedder_class,
)
from leettools.eds.str_embedder.sparse_embedder import (
    AbstractSparseEmbedder,
    get_sparse_embedder_class,
)


class EmbedderSettings(BaseModel):
    embedder_type: str = Field(..., description="The type of the embedder")
    dense_embedder: str = Field(
        ...,
        description="The dense embedder name, used by the factory class to create the actual embedder.",
    )
    dense_embedder_params: Dict[str, Any] = Field(
        {}, description="The parameters for the dense embedder."
    )
    sparse_embedder: str = Field(
        None,
        description="The sparse embedder name, used by the factory class to create the actual embedder.",
    )
    sparse_embedder_params: Dict[str, Any] = Field(
        {}, description="The parameters for the sparse embedder."
    )


def _get_embedder_settings_for_user(context: Context, user: User) -> EmbedderSettings:
    """
    Get the default embedder params for the user. If no user settings are found,
    use the system default settings.

    If used in cli, the values from the environment variables have higher priority;
    if used in svc, the values from the user settings have higher priority.
    """

    user_settings_store = context.get_user_settings_store()
    settings = context.settings

    # the availabe user settings are defined in the settings.py
    # get_user_configurable_settings() method
    user_settings = user_settings_store.get_settings_for_user(user)

    embedder_type_us = user_settings.get_value("DEFAULT_EMBEDDER_TYPE", None)
    embedder_type_env = settings.DEFAULT_SEGMENT_EMBEDDER_TYPE
    dense_embedder_us = user_settings.get_value("DEFAULT_DENSE_EMBEDDER", None)
    dense_embedder_env = settings.DEFAULT_DENSE_EMBEDDER
    sparse_embedder_us = user_settings.get_value("DEFAULT_SPARSE_EMBEDDER", None)
    sparse_embedder_env = settings.DEFAULT_SPARSE_EMBEDDER

    if context.is_svc:
        # user setting has higher priority
        if embedder_type_us is not None and embedder_type_us != "":
            embedder_type = SegmentEmbedderType(embedder_type_us)
        else:
            embedder_type = SegmentEmbedderType(embedder_type_env)

        # right now we always have a dense embedder
        if dense_embedder_us is not None and dense_embedder_us != "":
            dense_embedder = dense_embedder_us
        else:
            dense_embedder = dense_embedder_env

        dense_embeder_class: AbstractDenseEmbedder = get_dense_embedder_class(
            dense_embedder, settings
        )
        dense_embedder_params = dense_embeder_class.get_default_params(context, user)
        if embedder_type == SegmentEmbedderType.SIMPLE:
            return EmbedderSettings(
                embedder_type=embedder_type,
                dense_embedder=dense_embedder,
                dense_embedder_params=dense_embedder_params,
            )

        if embedder_type != SegmentEmbedderType.HYBRID:
            raise exceptions.UnexpectedCaseException(
                f"Unknown embedder type: {embedder_type}"
            )

        if sparse_embedder_us is not None and sparse_embedder_us.value != "":
            sparse_embedder = sparse_embedder_us
        else:
            sparse_embedder = sparse_embedder_env

        sparse_embedder_class: AbstractSparseEmbedder = get_sparse_embedder_class(
            sparse_embedder, settings
        )
        sparse_embedder_params = sparse_embedder_class.get_default_params(context, user)
    else:
        # cli has higher priority
        if embedder_type_env is not None and embedder_type_env != "":
            embedder_type = SegmentEmbedderType(embedder_type_env)
        else:
            embedder_type = SegmentEmbedderType(embedder_type_us)

        if dense_embedder_env is not None and dense_embedder_env != "":
            dense_embedder = dense_embedder_env
        else:
            dense_embedder = dense_embedder_us

        dense_embeder_class: AbstractDenseEmbedder = get_dense_embedder_class(
            dense_embedder, settings
        )
        dense_embedder_params = dense_embeder_class.get_default_params(context, user)
        if embedder_type == SegmentEmbedderType.SIMPLE:
            return EmbedderSettings(
                embedder_type=embedder_type,
                dense_embedder=dense_embedder,
                dense_embedder_params=dense_embedder_params,
            )

        if embedder_type != SegmentEmbedderType.HYBRID:
            raise exceptions.UnexpectedCaseException(
                f"Unknown embedder type: {embedder_type}"
            )

        if sparse_embedder_env is not None and sparse_embedder_env != "":
            sparse_embedder = sparse_embedder_env
        else:
            sparse_embedder = sparse_embedder_us

        sparse_embedder_class: AbstractSparseEmbedder = get_sparse_embedder_class(
            sparse_embedder, settings
        )

    return EmbedderSettings(
        embedder_type=embedder_type,
        dense_embedder=dense_embedder,
        dense_embedder_params=dense_embedder_params,
        sparse_embedder=sparse_embedder,
        sparse_embedder_params=sparse_embedder_params,
    )


def set_kb_create_embedder_params(
    kb_create: KBCreate, display_logger: Optional[EventLogger] = None
) -> KBCreate:
    """
    Fill in the embedder params for the KB create object.
    """
    from leettools.context_manager import ContextManager
    from leettools.eds.str_embedder.dense_embedder import get_dense_embedder_class

    if display_logger is None:
        display_logger = logger()

    context = ContextManager().get_context()
    settings = context.settings
    user_store = context.get_user_store()
    user = user_store.get_user_by_uuid(kb_create.user_uuid)
    if user is None:
        raise exceptions.EntityNotFoundException(
            entity_name=kb_create.user_uuid, entity_type="User"
        )

    embedder_settings = None
    if kb_create.embedder_type is None or kb_create.embedder_type == "":
        display_logger.debug(
            "No embedder type is set in KBCreate, using user settings."
        )
        embedder_settings = _get_embedder_settings_for_user(context, user)
        kb_create.embedder_type = embedder_settings.embedder_type
        kb_create.dense_embedder = embedder_settings.dense_embedder
        kb_create.dense_embedder_params = embedder_settings.dense_embedder_params
        kb_create.sparse_embedder = embedder_settings.sparse_embedder
        kb_create.sparse_embedder_params = embedder_settings.sparse_embedder_params
    else:
        display_logger.debug(
            f"Embedder type is set in KBCreate: {kb_create.embedder_type}"
        )
        if kb_create.dense_embedder is None or kb_create.dense_embedder == "":
            display_logger.debug(
                "No dense embedder is set in KBCreate, using user settings."
            )
            embedder_settings = _get_embedder_settings_for_user(context, user)
            kb_create.dense_embedder = embedder_settings.dense_embedder
            kb_create.dense_embedder_params = embedder_settings.dense_embedder_params
        else:
            display_logger.debug(
                f"Dense embedder is set in KBCreate: {kb_create.dense_embedder}"
            )
            if (
                kb_create.dense_embedder_params == None
                or kb_create.dense_embedder_params == {}
            ):
                display_logger.debug(
                    "No dense embedder params are set in KBCreate, using default params."
                )
                dense_embedder_class: AbstractDenseEmbedder = get_dense_embedder_class(
                    kb_create.dense_embedder, settings
                )
                kb_create.dense_embedder_params = (
                    dense_embedder_class.get_default_params(context, user)
                )
            else:
                # the dense embedder params are passed in, just use them
                display_logger.debug(
                    f"Dense embedder params are set in KBCreate: {kb_create.dense_embedder_params}"
                )

    display_logger.info(
        f"Final value: Embedder type for KB {kb_create.name} is {kb_create.embedder_type}"
    )
    display_logger.info(
        f"Final value: Dense Embedder for KB {kb_create.name} is "
        f"{kb_create.dense_embedder} and params {kb_create.dense_embedder_params}"
    )

    if kb_create.embedder_type == SegmentEmbedderType.HYBRID:
        if kb_create.sparse_embedder is None or kb_create.sparse_embedder == "":
            if embedder_settings == None:
                embedder_settings = _get_embedder_settings_for_user(context, user)
            kb_create.sparse_embedder = embedder_settings.sparse_embedder
            kb_create.sparse_embedder_params = embedder_settings.sparse_embedder_params
        else:
            if (
                kb_create.sparse_embedder_params is None
                or kb_create.sparse_embedder_params == {}
            ):
                from leettools.eds.str_embedder.sparse_embedder import (
                    get_sparse_embedder_class,
                )

                sparse_embedder_class: AbstractSparseEmbedder = (
                    get_sparse_embedder_class(kb_create.sparse_embedder, settings)
                )
                kb_create.sparse_embedder_params = (
                    sparse_embedder_class.get_default_params(context, user)
                )
            else:
                # the sparse embedder params are passed in, just use them
                pass

        display_logger.info(
            f"Sparse Embedder for KB {kb_create.name} is "
            f"{kb_create.sparse_embedder} and params {kb_create.sparse_embedder_params}"
        )
    return kb_create
