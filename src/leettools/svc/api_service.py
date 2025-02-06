import traceback

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from leettools.common.exceptions import (
    EdsExceptionBase,
    EntityNotFoundException,
    InsufficientBalanceException,
)
from leettools.common.logging import logger
from leettools.settings import SystemSettings
from leettools.svc.api.v1.api import ServiceAPIRouter


class APIService:
    def __init__(self, settings: SystemSettings):
        logger().info(f"SystemSettings: {settings}")
        self.app = FastAPI(
            title=settings.PROJECT_NAME,
        )
        self.api_router = ServiceAPIRouter()
        self.app.include_router(self.api_router, prefix=settings.API_V1_STR)

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            if logger().log_noop_level < 3:
                response = await call_next(request)
                return response

            # Log basic request information
            logger().noop(f"Incoming Request Method: {request.method}", noop_lvl=3)
            logger().noop(f"URL: {request.url}", noop_lvl=3)
            logger().noop(f"Headers: {request.headers}", noop_lvl=3)

            # Optionally, log the request body.
            # NOTE: Reading the body here can consume the stream, so if your endpoint also needs it,
            # you must set up the request to be able to read the body again.
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body_str = body_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    body_str = str(body_bytes)
                logger().noop(f"Body: {body_str}", noop_lvl=4)

            # Process the request and get the response
            response = await call_next(request)
            return response

        @self.app.get("/")
        def read_root():
            return {"Status": "OK"}

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            # Custom handling logic
            trace = traceback.format_exc()
            logger().error(exc)
            logger().error(trace)
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "name": "HTTPException",
                    "message": str(exc),
                    "detail": exc.detail,
                },
            )

        @self.app.exception_handler(InsufficientBalanceException)
        async def insufficient_balance_exception_handler(
            request: Request, exc: InsufficientBalanceException
        ):
            # Custom handling logic
            trace = traceback.format_exc()
            logger().error(exc)
            logger().error(trace)
            return JSONResponse(
                status_code=429,
                content={
                    "name": exc.exception_name,
                    "message": exc.exception_message,
                    "detail": exc.exception_trace,
                },
            )

        @self.app.exception_handler(EntityNotFoundException)
        async def entity_not_found_exception_handler(
            request: Request, exc: EntityNotFoundException
        ):
            # Custom handling logic
            trace = traceback.format_exc()
            logger().error(exc)
            logger().error(trace)
            return JSONResponse(
                status_code=404,
                content={
                    "name": exc.exception_name,
                    "message": exc.exception_message,
                    "detail": exc.exception_trace,
                },
            )

        @self.app.exception_handler(EdsExceptionBase)
        async def eds_exception_handler(request: Request, exc: EdsExceptionBase):
            # Custom handling logic
            trace = traceback.format_exc()
            logger().error(exc)
            logger().error(trace)
            return JSONResponse(
                status_code=500,
                content={
                    "name": exc.exception_name,
                    "message": exc.exception_message,
                    "detail": exc.exception_trace,
                },
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            # Custom handling logic
            trace = traceback.format_exc()
            logger().error(exc)
            logger().error(trace)
            return JSONResponse(
                status_code=500,
                content={"name": "Exception", "message": str(exc), "detail": trace},
            )

    def run(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        logger().info(f"Starting the application on host {host} and port {port}")
        uvicorn.run(self.app, host=host, port=port)
