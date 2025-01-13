from pymilvus import model

from leettools.common.logging import logger
from leettools.common.singleton_meta import SingletonMeta
from leettools.context_manager import Context, ContextManager

"""
Right now the reranker and embedder are using the system-wide settings and shared
by all the usres. Only the intention detection, query rewriting, and final inference
are using the customizable user settings through the api-provider-config.

One consideration is that the reranker and embedder are too technical to expose to 
the users, and the choices should be determined before querying time. Especially for
embedders, we can't switch embedders after the documents are processed.
"""


class SpladeFunction(metaclass=SingletonMeta):
    # TODO: make a thread-safe client pool
    def __init__(self):
        if not hasattr(
            self, "initialized"
        ):  # This ensures __init__ is only called once
            self.initialized = True
            context = ContextManager().get_context()  # type: Context
            settings = context.settings
            model_name = settings.DEFAULT_SPLADE_EMBEDDING_MODEL
            logger().info(
                f"Initializing SPLADEEmbedder model in constuctor {model_name} ..."
            )
            splade_ef = model.sparse.SpladeEmbeddingFunction(
                model_name=model_name, device="cpu"
            )
            self.function_mappings = {model_name: splade_ef}

    def get_function(self, model_name: str) -> model.sparse.SpladeEmbeddingFunction:
        logger().info(f"Getting SPLADEEmbedder function {model_name} ...")
        if model_name not in self.function_mappings:
            logger().info(
                f"Initializing SPLADEEmbedder model in get_function {model_name} ..."
            )
            splade_ef = model.sparse.SpladeEmbeddingFunction(
                model_name=model_name, device="cpu"
            )
            self.function_mappings[model_name] = splade_ef
        return self.function_mappings[model_name]
