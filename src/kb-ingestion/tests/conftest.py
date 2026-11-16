"""Pytest fixtures for kb-ingestion."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

importlib.import_module("kb-ingestion.app.main")
for _original in list(sys.modules):
    if _original.startswith("kb-ingestion"):
        _aliased = _original.replace("kb-ingestion", "kb_ingestion")
        sys.modules[_aliased] = sys.modules[_original]

from kb_ingestion.app.adapters.object_store import InMemoryObjectStore
from kb_ingestion.app.main import create_app


@pytest.fixture
def object_store() -> InMemoryObjectStore:
    return InMemoryObjectStore()


@pytest.fixture
def client(object_store: InMemoryObjectStore) -> TestClient:
    app = create_app(object_store=object_store)
    return TestClient(app)