import sys

import click
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import ContextManager
from leettools.eds.str_embedder._impl.dense_embedder_sentence_transformer import (
    DenseEmbedderSentenceTransformer,
)
from leettools.eds.str_embedder.dense_embedder import AbstractDenseEmbedder
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
    DenseEmbeddings,
)
from leettools.settings import SystemSettings


class EmbeddingRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        context = ContextManager().get_context()
        self.embedder: AbstractDenseEmbedder = DenseEmbedderSentenceTransformer(
            org=None,
            kb=None,
            user=None,
            context=context,
        )

        @self.get("/")
        def get_model():
            """
            Dummy hello world end point for tests.
            """
            return {
                "model_name": self.embedder.get_model_name(),
            }

        @self.post("/", response_model=DenseEmbeddings)
        def embed(request: DenseEmbeddingRequest):
            """
            Embed a list of strings
            """
            try:
                return self.embedder.embed(request)
            except Exception as e:
                err_msg = f"Failed to embed request: {request}\nException: {e}"
                logger().error(err_msg)
                print(err_msg, file=sys.stderr)
                raise HTTPException(status_code=500, detail=err_msg)


class EmbeddingService:
    def __init__(self, settings: SystemSettings):
        self.app = FastAPI(
            title=settings.PROJECT_NAME + "_embeder",
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.api_router = APIRouter()

        self.embed_router = EmbeddingRouter()
        self.api_router.include_router(
            self.embed_router, prefix="/embed", tags=["embedder"]
        )

        self.app.include_router(self.api_router, prefix=settings.API_V1_STR)

        @self.app.get("/")
        def read_root():
            """
            Dummy hello world end point for tests.
            """
            return {
                "Hello": "This is the embedding service!",
            }

    def run(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        logger().info(f"Starting the embedding service on host {host} and port {port}")
        uvicorn.run(self.app, host=host, port=port)


def _start_service(settings: SystemSettings, host: str, port: int) -> None:
    my_service = EmbeddingService(settings)
    my_service.run(host=host, port=port)


@click.command()
@click.option(
    "-h",
    "--host",
    "host",
    default="0.0.0.0",
    required=False,
    help="The host ip address to run the embedding service",
    show_default=True,
)
@click.option(
    "-p",
    "--port",
    "port",
    default=8001,
    required=False,
    help="The port to run the embedding service",
    show_default=True,
)
@click.option(
    "-l",
    "--log-level",
    "log_level",
    default="INFO",
    required=False,
    type=click.Choice(
        [
            "INFO",
            "DEBUG",
            "WARNING",
            "ERROR",
        ],
        case_sensitive=False,
    ),
    help="the default log level for all loggers",
    show_default=True,
)
def start_service(
    host: str,
    port: int,
    log_level: str,
) -> None:
    EventLogger.set_global_default_level(log_level.upper())
    context = ContextManager().get_context()  # type: Context
    _start_service(settings=context.settings, host=host, port=port)


if __name__ == "__main__":
    start_service()
