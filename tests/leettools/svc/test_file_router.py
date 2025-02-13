from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient

from leettools.context_manager import Context, ContextManager
from leettools.svc.api.v1.routers.file_router import FileRouter


def test_file_router(tmp_path):

    context = ContextManager().get_context()  # type: Context
    settings = context.settings
    OLD_DATA_ROOT = settings.DATA_ROOT
    settings.DATA_ROOT = tmp_path

    try:
        _test_file_router(tmp_path)
    finally:
        settings.DATA_ROOT = OLD_DATA_ROOT


def _test_file_router(tmp_path):
    filename = "test.txt"
    with open(tmp_path / filename, "w") as f:
        f.write("Hello, World!")

    file_path = tmp_path / filename
    uri = Path(file_path).absolute().as_uri()

    router = FileRouter()
    client = TestClient(router)

    response = client.get(f"/raw", params={"uri": uri})
    assert response.status_code == 200

    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.content == b"Hello, World!"

    try:
        response = client.get(f"/raw", params={"uri": uri + "x"})
    except HTTPException as e:
        assert e.status_code == 404

    try:
        response = client.get(f"/raw", params={"uri": "file:///etc/passwd"})
    except HTTPException as e:
        assert e.status_code == 400

    try:
        response = client.get(f"/raw", params={"uri": "etc/passwd"})
    except HTTPException as e:
        assert e.status_code == 404
