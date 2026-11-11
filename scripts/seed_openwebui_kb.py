#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx",
# ]
# ///

"""Seed an Open WebUI knowledge collection with project markdown files.

This is a local-dev helper, not the production ingestion pipeline (Phase C).
It signs into Open WebUI with the no-auth default admin credentials,
creates a knowledge collection, and uploads selected Markdown files so
there is test content available in Workspace > Knowledge.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "http://127.0.0.1:3100")
DEFAULT_EMAIL = "admin@localhost"
DEFAULT_PASSWORD = "admin"


def _signin(client: httpx.Client) -> str:
    r = client.post(
        f"{OPENWEBUI_URL}/api/v1/auths/signin",
        json={"email": DEFAULT_EMAIL, "password": DEFAULT_PASSWORD},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["token"]


def _create_knowledge(client: httpx.Client, token: str, name: str) -> dict[str, Any]:
    r = client.post(
        f"{OPENWEBUI_URL}/api/v1/knowledge/create",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "description": "Test knowledge base seeded from project markdown files."},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def _find_knowledge(client: httpx.Client, token: str, name: str) -> dict[str, Any] | None:
    r = client.get(
        f"{OPENWEBUI_URL}/api/v1/knowledge/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()
    for item in r.json().get("items", []):
        if item.get("name") == name:
            return item
    return None


def _create_default_model(
    client: httpx.Client,
    token: str,
    model_id: str,
    base_model_id: str,
    name: str,
    knowledge_id: str,
    knowledge_name: str,
) -> dict[str, Any]:
    payload = {
        "id": model_id,
        "base_model_id": base_model_id,
        "name": name,
        "meta": {
            "description": "Default assistant for hoster.by Knowledge Base with project docs.",
            "knowledge": [
                {
                    "id": knowledge_id,
                    "name": knowledge_name,
                    "type": "collection",
                    "collection_name": knowledge_id,
                }
            ],
        },
        "params": {
            "system": "You are a helpful assistant for the hoster.by knowledge base. Use the attached project documentation to answer questions accurately."
        },
        "access_grants": [],
        "is_active": True,
    }
    r = client.post(
        f"{OPENWEBUI_URL}/api/v1/models/create",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=10,
    )
    if r.status_code == 401 and "already registered" in r.text.lower():
        r = client.post(
            f"{OPENWEBUI_URL}/api/v1/models/model/update",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=10,
        )
    r.raise_for_status()
    return r.json()


def _set_default_model(client: httpx.Client, token: str, model_id: str) -> dict[str, Any]:
    r = client.post(
        f"{OPENWEBUI_URL}/api/v1/configs/models",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "DEFAULT_MODELS": model_id,
            "DEFAULT_PINNED_MODELS": model_id,
            "MODEL_ORDER_LIST": [model_id],
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def _upload_file(
    client: httpx.Client,
    token: str,
    knowledge_id: str,
    file_path: Path,
) -> dict[str, Any]:
    content = file_path.read_bytes()
    filename = file_path.name
    mime, _ = mimetypes.guess_type(str(file_path))
    metadata = json.dumps({"knowledge_id": knowledge_id})
    files = {"file": (filename, content, mime or "text/markdown")}
    data = {"metadata": metadata, "process": "true", "process_in_background": "true"}
    r = client.post(
        f"{OPENWEBUI_URL}/api/v1/files/",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def _collect_markdown_files(root: Path) -> list[Path]:
    globs = [
        "specs/corporate-kb/*.md",
        "specs/corporate-kb/components/*.md",
        "specs/corporate-kb/contracts/*.md",
        "specs/corporate-kb/adr/*.md",
    ]
    found: set[Path] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if path.is_file() and path.stat().st_size > 0:
                found.add(path)
    return sorted(found)


def main() -> int:
    name = os.environ.get("KB_SEED_NAME", "corp-ai-db project docs")
    model_id = os.environ.get("KB_MODEL_ID", "hoster-assistant")
    base_model_id = os.environ.get("KB_BASE_MODEL_ID", "kimi-for-coding")
    with httpx.Client() as client:
        print(f"Signing into {OPENWEBUI_URL} as default admin...")
        token = _signin(client)

        existing = _find_knowledge(client, token, name)
        if existing:
            print(f"Using existing knowledge collection: {existing['id']}")
            knowledge = existing
        else:
            print("Creating knowledge collection...")
            knowledge = _create_knowledge(client, token, name)
        knowledge_id = knowledge["id"]

        files = _collect_markdown_files(REPO_ROOT)
        print(f"Uploading {len(files)} markdown files...")
        for path in files:
            try:
                _upload_file(client, token, knowledge_id, path)
                print(f"  uploaded: {path.relative_to(REPO_ROOT)}")
            except httpx.HTTPStatusError as exc:
                print(f"  failed: {path.relative_to(REPO_ROOT)} -> {exc.response.status_code} {exc.response.text[:200]}")
            except Exception as exc:  # noqa: BLE001
                print(f"  failed: {path.relative_to(REPO_ROOT)} -> {exc}")

        print(f"Creating default knowledge-backed model '{model_id}'...")
        _create_default_model(
            client,
            token,
            model_id=model_id,
            base_model_id=base_model_id,
            name="hoster.by Assistant",
            knowledge_id=knowledge_id,
            knowledge_name=name,
        )

        print("Setting model as default...")
        _set_default_model(client, token, model_id)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
