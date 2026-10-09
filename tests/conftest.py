import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from server.db import init_db
from server.main import app
from server.settings import get_settings


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def test_client(temp_db_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", temp_db_path)
    settings = get_settings()
    settings.db_path = temp_db_path
    init_db(temp_db_path)

    with TestClient(app) as client:
        yield client
