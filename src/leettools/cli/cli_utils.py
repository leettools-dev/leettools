import os
from typing import Any, Dict, Optional, Tuple

import click

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.utils import config_utils
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KBCreate, KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User

LINE_WIDTH = 100
DELIM_LINE = "=" * LINE_WIDTH


def parse_name_value(
    ctx: click.Context, param: click.Parameter, value: Any
) -> Dict[str, Any]:
    """
    Parses name=value pairs from the command line.
    """
    params = {}
    for item in value:
        if "=" not in item:
            raise click.BadParameter(f"Invalid format '{item}'. Expected name=value.")
        name, val = item.split("=", 1)
        params[name.strip()] = val.strip()
    return params


def load_params_from_file(file_path: str) -> Dict[str, Any]:
    """
    Loads parameters from a file containing name=value pairs.
    """
    params = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    if "=" not in line:
                        raise ValueError(f"Invalid line '{line}'. Expected name=value.")
                    name, val = line.split("=", 1)
                    params[name.strip()] = val.strip()
    except Exception as e:
        raise click.ClickException(f"Error reading parameter file: {e}")
    return params


def setup_org_kb_user(
    context: Context,
    org_name: str,
    kb_name: str,
    username: str,
    adhoc_kb: Optional[bool] = False,
) -> Tuple[Org, KnowledgeBase, User]:
    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()
    user_store = context.get_user_store()

    if username is None:
        user = User.get_admin_user()
    else:
        user = user_store.get_user_by_name(username)
        if user is None:
            raise exceptions.EntityNotFoundException(
                entity_name=username, entity_type="User"
            )

    # we will report error if the org does not exist
    # usually we do not specify the org name
    if org_name is None:
        org = org_manager.get_default_org()
    else:
        org = org_manager.get_org_by_name(org_name)
    if org is None:
        raise exceptions.EntityNotFoundException(
            entity_name=org_name, entity_type="Organization"
        )

    if adhoc_kb:
        if kb_name is None:
            raise exceptions.UnexpectedCaseException(
                "Adhoc KB creation requires a kb_name to be specified."
            )
        # adhoc kb is created with auto_schedule=False
        # also with embedder type set to SIMPLE
        kb = kb_manager.get_kb_by_name(org, kb_name)
        # we will create the kb if it does not exist
        if kb == None:
            kb = kb_manager.add_kb(
                org=org,
                kb_create=KBCreate(
                    name=kb_name,
                    description=f"Created automatically by CLI command",
                    user_uuid=user.user_uuid,
                    auto_schedule=False,
                    enable_contextual_retrieval=context.settings.ENABLE_CONTEXTUAL_RETRIEVAL,
                ),
            )
    else:
        if kb_name is None:
            kb_name = context.settings.DEFAULT_KNOWLEDGEBASE_NAME
        kb = kb_manager.get_kb_by_name(org, kb_name)
        # we will create the kb if it does not exist
        if kb == None:
            kb = kb_manager.add_kb(
                org,
                KBCreate(
                    name=kb_name,
                    description=f"Created automatically by CLI command",
                    user_uuid=user.user_uuid,
                    auto_schedule=True,
                    enable_contextual_retrieval=context.settings.ENABLE_CONTEXTUAL_RETRIEVAL,
                ),
            )

    # check if the kb's embedder has correct setup
    ignore_embedded_check = config_utils.value_to_bool(
        os.environ.get("EDS_IGNORE_EMBEDDET_CHECK", False)
    )
    if not ignore_embedded_check:
        from leettools.eds.str_embedder.dense_embedder import (
            AbstractDenseEmbedder,
            create_dense_embedder_for_kb,
            get_dense_embedder_class,
        )

        logger().info(f"Checking dense embedder for KB {kb_name} ...")
        dense_embedder_kb = create_dense_embedder_for_kb(
            context=context,
            org=org,
            kb=kb,
            user=user,
        )
        default_dense_embedder_class = get_dense_embedder_class(None, context.settings)
        logger().info("Getting default dense embedder from settings to compare ...")
        default_dense_embedder: AbstractDenseEmbedder = default_dense_embedder_class(
            context=context
        )
        if not dense_embedder_kb.is_compatible(default_dense_embedder):
            click.secho(
                f"Warning: KB {kb_name} uses a dense embedder that is not compatible "
                f"with the default specified in {context.settings.env_file}:\n"
                f"KB embedder: {dense_embedder_kb.__class__.__name__}"
                f"[model: {dense_embedder_kb.get_model_name()}]"
                f"[dimension: {dense_embedder_kb.get_dimension()}]\n"
                f"Default    : {default_dense_embedder_class.__name__}"
                f"[model: {default_dense_embedder.get_model_name()}]"
                f"[dimension: {default_dense_embedder.get_dimension()}].",
                err=True,
                fg="yellow",
            )
    else:
        logger().info(
            f"Skipping embedder check for KB {kb_name} as per EDS_IGNORE_EMBEDDET_CHECK."
        )

    return org, kb, user
