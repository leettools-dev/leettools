from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from leettools.common.logging import logger
from leettools.svc.api_router_base import APIRouterBase


class FileRouter(APIRouterBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        self.doc_store = context.get_repo_manager().get_document_store()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()

        @self.get("/raw")
        async def read_raw_document(uri: str) -> FileResponse:
            """
            Endpoint to return a file based on a local file URI (absolute path).

            Args:
            file_path (str): The absolute path to the file.

            Returns:
            FileResponse: A response object that serves the specified file directly.

            Raises:
            HTTPException: If the file does not exist or cannot be accessed.
            """
            logger().debug(f"Reading raw document from {uri}")

            safe_base_path = Path(self.settings.DATA_ROOT)
            incoming_file_path = Path("/incoming")
            uploads_file_path = Path("/app/uploads")

            if uri.startswith("file://"):
                uri = uri[7:]
            elif uri.startswith("file:"):
                uri = uri[5:]
            absolute_file_path = Path(uri)
            logger().debug(f"Absolute file path: {absolute_file_path}")

            # Resolve to absolute path and check if it's within safe_base_path
            if not absolute_file_path.resolve().is_absolute():
                raise HTTPException(
                    status_code=400,
                    detail=f"File path {absolute_file_path}is not absolute.",
                )

            if self.settings.is_production:
                # This security check assumes files are served from a subdirectory `safe_dir`.
                parents = absolute_file_path.resolve().parents
                if (
                    not safe_base_path.resolve() in parents
                    and not incoming_file_path.resolve() in parents
                    and not uploads_file_path.resolve() in parents
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=f"File path {absolute_file_path} not under safe paths.",
                    )

            if not absolute_file_path.exists() or not absolute_file_path.is_file():
                raise HTTPException(
                    status_code=404, detail=f"File {absolute_file_path} not found."
                )

            return FileResponse(str(absolute_file_path))
