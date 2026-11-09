"""Path normalization validator (NFC, separators, parent references)."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PathCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


def canonical_document_path(path: str) -> str | None:
    """Return NFC-normalized repository-relative path or None if invalid.

    Rules derived from front-matter / index-snapshot path invariants:
    - NFC Unicode normalization.
    - Forward slashes only; backslashes rejected.
    - No `..` segments.
    - No absolute paths (must not start with `/`).
    - No trailing slash except root `/` (which is not a document path).
    """
    path = unicodedata.normalize("NFC", path)
    if path == "":
        return None
    if "/" not in path and "\\" not in path:
        # Simple file name in root.
        if path in (".", ".."):
            return None
        return path
    if "\\" in path:
        return None
    if path.startswith("/"):
        return None
    if path.endswith("/"):
        return None
    parts = path.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    return path


def absolute_relative_lossless(absolute: str, relative: str) -> bool:
    """Check that `/pricing` <-> `pricing` mapping is lossless."""
    if absolute.startswith("/"):
        return absolute.lstrip("/") == relative
    return absolute == relative.lstrip("/")


class PathValidator:
    """Validate path normalization cases loaded from a YAML fixture."""

    def __init__(
        self, fixture: dict[str, Any], schema_validate=None
    ) -> None:
        self.fixture = fixture
        self.schema_validate = schema_validate

    @staticmethod
    def _minimal_origin(source_id: str) -> dict[str, Any]:
        """Return a minimal source-origin object with the given source_id."""
        return {
            "schema_version": "source-origin-v1",
            "source_id": source_id,
            "source_binding_id": "test-binding",
            "source_object_id": "test-object",
            "source_version": "test-version",
            "source_content_sha256": "0" * 64,
            "source_ref": "test-ref",
            "observed_at": "2026-01-01T00:00:00Z",
            "ownership_mode": "curated",
        }

    def validate(self) -> list[PathCheck]:
        checks: list[PathCheck] = []

        # Absolute/relative boundary pairs.
        for pair in self.fixture.get("absolute_relative_pairs", []):
            absolute = pair["absolute"]
            relative = pair["relative"]
            ok = absolute_relative_lossless(absolute, relative)
            checks.append(
                PathCheck(
                    id=f"paths.absolute_relative_lossless.{absolute}",
                    status="PASS" if ok else "FAIL",
                    expected=f"{absolute} <-> {relative} mapping is lossless",
                    actual=f"{absolute} <-> {relative} = {ok}",
                    details={
                        "absolute": absolute,
                        "relative": relative,
                        "lossless": ok,
                    },
                )
            )

        # Ambiguous paths must be rejected.
        for bad in self.fixture.get("ambiguous_paths", []):
            path = bad["path"]
            normalized = canonical_document_path(path)
            rejected = normalized is None
            checks.append(
                PathCheck(
                    id=f"paths.ambiguous_rejected.{path}",
                    status="PASS" if rejected else "FAIL",
                    expected=f"ambiguous path {path} is rejected",
                    actual=f"rejected={rejected}, normalized={normalized}",
                    details={
                        "path": path,
                        "normalized": normalized,
                        "rejected": rejected,
                    },
                )
            )

        # NFC/NFD duplicates.
        for item in self.fixture.get("nfc_nfd", []):
            nfc = unicodedata.normalize("NFC", item["nfc"])
            nfd = unicodedata.normalize("NFC", item["nfd"])
            duplicate = nfc == nfd
            checks.append(
                PathCheck(
                    id=f"paths.nfc_nfd_duplicate.{item['nfc']}",
                    status="PASS" if duplicate else "FAIL",
                    expected="NFC/NFD duplicates are detected",
                    actual=f"NFC(nfc)==NFC(nfd): {duplicate}",
                    details={
                        "nfc": item["nfc"],
                        "nfd": item["nfd"],
                        "duplicate": duplicate,
                    },
                )
            )

        # Source ID case preservation (DOC-0001 exact case).
        for item in self.fixture.get("source_id_cases", []):
            source_id = item["source_id"]
            expected_valid = item.get("valid", True)
            origin = self._minimal_origin(source_id)
            err = None
            if self.schema_validate:
                err = self.schema_validate("source-origin.schema.json", origin)
            schema_ok = err is None
            ok = schema_ok == expected_valid
            checks.append(
                PathCheck(
                    id=f"paths.source_id_case.{source_id}",
                    status="PASS" if ok else "FAIL",
                    expected=f"source_id '{source_id}' schema valid={expected_valid}",
                    actual=f"schema_valid={schema_ok}, error={err}",
                    details={"source_id": source_id, "valid": expected_valid, "error": err},
                )
            )

        return checks
