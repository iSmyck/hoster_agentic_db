"""Shared harness import helpers for unit tests.

Harness source files live in gitignored `_bmad-output/test-artifacts/t0*/`
directories. Tests load them via importlib so they stay isolated from each
other and gracefully skip when a harness directory is missing.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent

HARNESS_DIRS = {
    "t01_reporters": ROOT / "_bmad-output" / "test-artifacts" / "t01" / "reporters",
    "t02_validators": ROOT / "_bmad-output" / "test-artifacts" / "t02" / "validators",
    "t03a_validators": ROOT / "_bmad-output" / "test-artifacts" / "t03a" / "validators",
    "t03b_validators": ROOT / "_bmad-output" / "test-artifacts" / "t03b" / "validators",
    "t04a_validators": ROOT / "_bmad-output" / "test-artifacts" / "t04a" / "validators",
    "t04b_validators": ROOT / "_bmad-output" / "test-artifacts" / "t04b" / "validators",
    "t10a_harness": ROOT / "_bmad-output" / "test-artifacts" / "t10a",
    "t10b_harness": ROOT / "_bmad-output" / "test-artifacts" / "t10b",
}


def _ensure_package(name: str) -> types.ModuleType:
    if name not in sys.modules:
        pkg = types.ModuleType(name)
        pkg.__path__ = []
        sys.modules[name] = pkg
    return sys.modules[name]


def _load_module(full_name: str, file_path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(full_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


def _load_package_modules(
    package_prefix: str, package_dir: Path, module_names: list[str]
) -> Any:
    _ensure_package(package_prefix)
    loaded: dict[str, types.ModuleType] = {}
    for mod_name in module_names:
        full_name = f"{package_prefix}.{mod_name}"
        loaded[mod_name] = _load_module(full_name, package_dir / f"{mod_name}.py")
    return types.SimpleNamespace(**loaded)


def _load_individual_modules(package_dir: Path, module_names: list[str]) -> Any:
    loaded: dict[str, types.ModuleType] = {}
    for mod_name in module_names:
        loaded[mod_name] = _load_module(mod_name, package_dir / f"{mod_name}.py")
    return types.SimpleNamespace(**loaded)


@pytest.fixture(scope="session")
def t01_modules() -> Any:
    try:
        return _load_individual_modules(
            HARNESS_DIRS["t01_reporters"], ["json_reporter", "sanitize"]
        )
    except Exception as exc:
        pytest.skip(f"t01 reporters unavailable: {exc}")


@pytest.fixture(scope="session")
def t02_modules() -> Any:
    try:
        return _load_individual_modules(
            HARNESS_DIRS["t02_validators"], ["document_store", "paths"]
        )
    except Exception as exc:
        pytest.skip(f"t02 validators unavailable: {exc}")


@pytest.fixture(scope="session")
def t03a_modules() -> Any:
    try:
        return _load_individual_modules(HARNESS_DIRS["t03a_validators"], ["groups"])
    except Exception as exc:
        pytest.skip(f"t03a validators unavailable: {exc}")


@pytest.fixture(scope="session")
def t03b_modules() -> Any:
    try:
        return _load_individual_modules(
            HARNESS_DIRS["t03b_validators"], ["longest_prefix"]
        )
    except Exception as exc:
        pytest.skip(f"t03b validators unavailable: {exc}")


@pytest.fixture(scope="session")
def t04a_modules() -> Any:
    try:
        return _load_package_modules(
            "_t04a_test_pkg",
            HARNESS_DIRS["t04a_validators"],
            ["base", "idempotency", "stale_base"],
        )
    except Exception as exc:
        pytest.skip(f"t04a validators unavailable: {exc}")


@pytest.fixture(scope="session")
def t04b_modules() -> Any:
    try:
        return _load_package_modules(
            "_t04b_test_pkg",
            HARNESS_DIRS["t04b_validators"],
            ["base", "round_trip", "front_matter_boundary", "xss"],
        )
    except Exception as exc:
        pytest.skip(f"t04b validators unavailable: {exc}")


@pytest.fixture(scope="session")
def t10a_modules() -> Any:
    try:
        return _load_individual_modules(
            HARNESS_DIRS["t10a_harness"], ["run_t10a_tests"]
        )
    except Exception as exc:
        pytest.skip(f"t10a harness unavailable: {exc}")


@pytest.fixture(scope="session")
def t10b_modules() -> Any:
    try:
        return _load_individual_modules(
            HARNESS_DIRS["t10b_harness"], ["run_t10b_tests"]
        )
    except Exception as exc:
        pytest.skip(f"t10b harness unavailable: {exc}")
