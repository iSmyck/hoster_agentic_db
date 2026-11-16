#!/usr/bin/env python3
"""Live kb-ingestion checks against the local stack (synthetic fixtures)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[3]
load_dotenv(REPO / ".env", override=False)

INGEST = "http://127.0.0.1:8006"
OUTPUT = Path(__file__).resolve().parent / "live-stack-ingest.json"
EVIDENCE = REPO / "specs" / "corporate-kb" / "evidence" / "kb-ingestion" / "live-stack-ingest.md"
SPACE = "corp-kb/sales"
PATH = f"docs/kbi-live-{uuid.uuid4().hex[:10]}.md"
MARKDOWN = f"""---
schema_version: document-front-matter-v2
title: KBI live ingest
owner: author-1
status: draft
---

# KBI live ingest

Synthetic page {PATH}.
"""


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    expected: str,
    actual: str,
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": status,
            "expected": expected,
            "actual": actual[:500],
        }
    )


def main() -> int:
    checks: list[dict[str, Any]] = []
    client = httpx.Client(timeout=180)
    try:
        health = client.get(f"{INGEST}/health")
        _check(
            checks,
            "ingest.health",
            "PASS" if health.status_code == 200 else "FAIL",
            "kb-ingestion /health 200",
            f"status={health.status_code}",
        )

        upload = client.post(
            f"{INGEST}/api/kb/v1/ingest/convert",
            data={
                "space_id": "sales",
                "client_id": "live-stack",
                "data_profile": "strict",
            },
            files={"file": ("page.md", MARKDOWN.encode(), "text/markdown")},
        )
        _check(
            checks,
            "ingest.convert_upload",
            "PASS" if upload.status_code == 201 else "FAIL",
            "convert upload 201",
            f"status={upload.status_code} body={upload.text[:300]}",
        )
        object_id = ""
        if upload.status_code == 201:
            object_id = str(upload.json().get("object_id") or "")
            run = client.post(
                f"{INGEST}/api/kb/v1/ingest/convert/run",
                json={
                    "space_id": "sales",
                    "client_id": "live-stack",
                    "object_id": object_id,
                    "source_path": PATH,
                    "ownership_mode": "migrated",
                    "data_profile": "strict",
                },
            )
            _check(
                checks,
                "ingest.convert_run",
                "PASS" if run.status_code == 200 and run.json().get("status") == "ready" else "FAIL",
                "convert/run ready",
                f"status={run.status_code} body={run.text[:400]}",
            )

        register = client.post(
            f"{INGEST}/api/kb/v1/ingest/sources",
            json={
                "source_type": "n8n",
                "source_ref": "live-stack://synthetic",
                "credentials_ref": "ref:live-stack",
                "poll_interval": 3600,
                "space_id": SPACE,
                "data_profile": "strict",
                "validation_required": False,
                "auto_merge": True,
                "trusted": True,
            },
        )
        _check(
            checks,
            "ingest.source_register",
            "PASS" if register.status_code == 201 else "FAIL",
            "register trusted auto_merge source",
            f"status={register.status_code} body={register.text[:400]}",
        )
        source_id = ""
        if register.status_code == 201:
            source_id = str(register.json().get("source_id") or "")
            digest = hashlib.sha256(MARKDOWN.encode()).hexdigest()
            sync = client.post(
                f"{INGEST}/api/kb/v1/ingest/sources/{source_id}/sync",
                json={
                    "documents": [
                        {
                            "source_object_id": "live-1",
                            "source_version": "v1",
                            "sha256": digest,
                            "path": PATH,
                            "action": "upsert",
                            "ownership_mode": "source_managed",
                            "lines_changed": 12,
                            "markdown": MARKDOWN,
                        }
                    ]
                },
            )
            body = sync.text[:800]
            ok = sync.status_code == 200 and any(
                item.get("disposition") == "merged" for item in (sync.json().get("outcomes") or [])
            )
            _check(
                checks,
                "ingest.source_sync_auto_merge",
                "PASS" if ok else "FAIL",
                "source-sync auto-merge against live GO/GitLab",
                f"status={sync.status_code} body={body}",
            )
    finally:
        client.close()

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "claim": "VERIFIED(live-local-stack)"
        if all(item["status"] == "PASS" for item in checks)
        else "PARTIAL",
        "checks": checks,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# kb-ingestion live stack",
        "",
        f"Generated: {payload['generated_at']}",
        f"Claim: **{payload['claim']}**",
        "",
        "| ID | Status | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for item in checks:
        actual = item["actual"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {item['id']} | {item['status']} | {item['expected']} | {actual} |")
    EVIDENCE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = sum(1 for item in checks if item["status"] != "PASS")
    print(json.dumps({"failed": failed, "checks": checks}, indent=2)[:4000])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
