"""Unit tests for T02 document/path validators and Git blob hash."""

from __future__ import annotations

import hashlib
import unicodedata
from pathlib import Path
from typing import Any


def test_canonical_document_path(t02_modules: Any) -> None:
    cp = t02_modules.paths.canonical_document_path

    assert cp("pricing.md") == "pricing.md"
    assert cp("sales/pricing.md") == "sales/pricing.md"
    assert cp("") is None
    assert cp("/absolute.md") is None
    assert cp("../escape.md") is None
    assert cp("dir/") is None
    assert cp("dir/./file.md") is None
    assert cp("dir//file.md") is None
    assert cp("dir\\file.md") is None

    # NFC normalization: NFD input becomes NFC output.
    nfd = unicodedata.normalize("NFD", "цены.md")
    nfc = unicodedata.normalize("NFC", "цены.md")
    assert cp(nfd) == nfc


def test_absolute_relative_lossless(t02_modules: Any) -> None:
    fn = t02_modules.paths.absolute_relative_lossless

    assert fn("/pricing", "pricing") is True
    assert fn("pricing", "/pricing") is True
    assert fn("/pricing", "/pricing") is False
    assert fn("pricing", "pricing") is True
    assert fn("/pricing", "sales/pricing") is False
    assert fn("/sales/pricing", "pricing") is False


def test_path_validator_fixture(t02_modules: Any) -> None:
    fixture = {
        "absolute_relative_pairs": [{"absolute": "/pricing", "relative": "pricing"}],
        "ambiguous_paths": [
            {"path": "/absolute"},
            {"path": "../escape"},
        ],
        "nfc_nfd": [
            {
                "nfc": "цены.md",
                "nfd": unicodedata.normalize("NFD", "цены.md"),
            }
        ],
    }
    checks = t02_modules.paths.PathValidator(fixture).validate()

    assert any(
        c.id == "paths.absolute_relative_lossless./pricing" and c.status == "PASS"
        for c in checks
    )
    assert any(
        c.id == "paths.ambiguous_rejected./absolute" and c.status == "PASS"
        for c in checks
    )
    assert any(
        c.id == "paths.ambiguous_rejected.../escape" and c.status == "PASS"
        for c in checks
    )
    assert any(
        c.id.startswith("paths.nfc_nfd_duplicate.") and c.status == "PASS"
        for c in checks
    )


def test_canonical_path(t02_modules: Any) -> None:
    cp = t02_modules.document_store._canonical_path

    assert cp(Path("./file.md")) == "file.md"
    assert cp(Path("sales/pricing.md")) == "sales/pricing.md"


def test_git_blob_hash(t02_modules: Any, tmp_path: Path) -> None:
    root = tmp_path / "space"
    root.mkdir()
    content = "hello world\n"
    (root / "test.md").write_text(content, encoding="utf-8")

    space = t02_modules.document_store.load_space("sales", "repo1", root)
    assert len(space.documents) == 1
    doc = space.documents[0]

    content_bytes = content.encode("utf-8")
    expected_sha = hashlib.sha1(
        b"blob " + str(len(content_bytes)).encode("ascii") + b"\0" + content_bytes
    ).hexdigest()
    assert doc.revision_sha == expected_sha
    assert len(doc.content_sha256) == 64
    assert doc.path == "test.md"
