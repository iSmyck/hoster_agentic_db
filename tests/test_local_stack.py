"""Tests for local development stack orchestration."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def reset_env() -> None:
    """Clear G1_ALLOW_DESTRUCTIVE_RESET for each test."""
    original = os.environ.pop("G1_ALLOW_DESTRUCTIVE_RESET", None)
    yield
    if original is not None:
        os.environ["G1_ALLOW_DESTRUCTIVE_RESET"] = original
    else:
        os.environ.pop("G1_ALLOW_DESTRUCTIVE_RESET", None)


def _import_reset_func():
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "local_stack", os.path.join(os.path.dirname(__file__), "..", "scripts", "local_stack.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["local_stack"] = module
    spec.loader.exec_module(module)
    return module._reset_openwebui_users


@patch("sqlalchemy.create_engine")
def test_reset_openwebui_users_skipped_when_guard_unset(mock_create_engine, reset_env) -> None:
    """_reset_openwebui_users must not truncate tables unless explicitly allowed."""
    _reset_openwebui_users = _import_reset_func()
    _reset_openwebui_users()
    mock_create_engine.assert_not_called()


@patch("sqlalchemy.create_engine")
def test_reset_openwebui_users_runs_when_guard_set(mock_create_engine, reset_env) -> None:
    """_reset_openwebui_users truncates tables when G1_ALLOW_DESTRUCTIVE_RESET=1."""
    _reset_openwebui_users = _import_reset_func()
    os.environ["G1_ALLOW_DESTRUCTIVE_RESET"] = "1"

    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    mock_create_engine.return_value = mock_engine

    _reset_openwebui_users()

    mock_create_engine.assert_called_once()
    mock_conn.execute.assert_called_once()
    call_sql = mock_conn.execute.call_args[0][0].text
    assert "TRUNCATE" in call_sql.upper()
