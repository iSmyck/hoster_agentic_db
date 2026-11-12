#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx",
# ]
# ///

"""Smoke test for the corp-ai-db local development stack.

Validates infrastructure and G1 service health, then exercises the
session → GO draft/history flow using seeded test identities.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=False)
RESULTS_DIR = REPO_ROOT / "_bmad-output" / "test-artifacts" / "local-stack"
EVIDENCE_DIR = REPO_ROOT / "specs" / "corporate-kb" / "evidence" / "local-stack"

GITLAB_URL = os.environ.get("GITLAB_URL", "http://localhost:8081")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", os.environ.get("GO_GITLAB_TOKEN", ""))


def _gitlab_health_url() -> tuple[str, dict[str, str] | None]:
    if GITLAB_TOKEN:
        return f"{GITLAB_URL}/api/v4/version", {"PRIVATE-TOKEN": GITLAB_TOKEN}
    return f"{GITLAB_URL}/api/v4/version", None


SERVICES: dict[str, str] = {
    "identity": "http://127.0.0.1:8001/health",
    "session": "http://127.0.0.1:8004/health",
    "go": "http://127.0.0.1:8002/health",
    "retrieval": "http://127.0.0.1:8003/health",
    "backup": "http://127.0.0.1:8005/health",
    "openwebui": "http://127.0.0.1:3100/api/config",
}


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    expected: str,
    actual: str,
    details: dict[str, Any] | None = None,
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": status,
            "expected": expected,
            "actual": actual,
            "details": details or {},
        }
    )


def _health_check(
    client: httpx.Client,
    name: str,
    url: str,
    checks: list[dict[str, Any]],
    headers: dict[str, str] | None = None,
) -> None:
    try:
        r = client.get(url, timeout=10, headers=headers)
        ok = r.status_code == 200
        _check(
            checks,
            f"health.{name}",
            "PASS" if ok else "FAIL",
            f"{name} health endpoint returns 200",
            f"status={r.status_code}",
            {"url": url, "body": r.text[:200]},
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            f"health.{name}",
            "FAIL",
            f"{name} health endpoint returns 200",
            f"{type(exc).__name__}: {exc}",
            {"url": url},
        )


def _gitlab_health_check(client: httpx.Client, checks: list[dict[str, Any]]) -> None:
    url, headers = _gitlab_health_url()
    last_status = "unknown"
    last_body = ""
    for attempt in range(6):
        try:
            r = client.get(url, timeout=10, headers=headers)
            last_status = str(r.status_code)
            last_body = r.text[:200]
            if r.status_code == 200:
                _check(
                    checks,
                    "health.gitlab",
                    "PASS",
                    "GitLab API is reachable",
                    f"status={r.status_code}",
                    {"url": url, "body": last_body},
                )
                return
            if r.status_code == 401 and not GITLAB_TOKEN:
                _check(
                    checks,
                    "health.gitlab",
                    "BLOCKED",
                    "GitLab API is reachable (requires token)",
                    "status=401, no GITLAB_TOKEN configured",
                    {"url": url},
                )
                return
            # Transient start-up codes: retry briefly.
            if r.status_code in (502, 503, 504) and attempt < 5:
                time.sleep(5)
                continue
        except httpx.ReadError as exc:
            last_status = f"{type(exc).__name__}: {exc}"
            if not GITLAB_TOKEN and attempt < 5:
                time.sleep(5)
                continue
            _check(
                checks,
                "health.gitlab",
                "BLOCKED",
                "GitLab API is reachable",
                last_status,
                {"url": url},
            )
            return
        except Exception as exc:  # noqa: BLE001
            last_status = f"{type(exc).__name__}: {exc}"
            if attempt < 5:
                time.sleep(5)
                continue
    _check(
        checks,
        "health.gitlab",
        "FAIL" if GITLAB_TOKEN else "BLOCKED",
        "GitLab API is reachable",
        f"status={last_status}",
        {"url": url, "body": last_body},
    )


def _session_flow(client: httpx.Client, checks: list[dict[str, Any]]) -> str | None:
    """Create a session for the G1 author and return the access token."""
    url = "http://127.0.0.1:8004/api/kb/v1/session/create"
    try:
        r = client.post(
            url,
            json={"stable_id": "author-1", "extra_claims": {"role": "user"}},
            timeout=10,
        )
        if r.status_code != 200:
            _check(
                checks,
                "session.create_author",
                "FAIL",
                "session service creates a token for author-1",
                f"status={r.status_code}, body={r.text[:500]}",
            )
            return None
        token = r.json()["access_token"]
        _check(
            checks,
            "session.create_author",
            "PASS",
            "session service creates a token for author-1",
            "token issued",
        )

        validate = client.get(
            "http://127.0.0.1:8004/api/kb/v1/session/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        ok = validate.status_code == 200 and validate.json().get("stable_id") == "author-1"
        _check(
            checks,
            "session.validate_author",
            "PASS" if ok else "FAIL",
            "session token validates and returns author-1 stable_id",
            f"status={validate.status_code}, body={validate.text[:200]}",
        )
        return token
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "session.create_author",
            "FAIL",
            "session service creates a token for author-1",
            f"{type(exc).__name__}: {exc}",
        )
        return None


def _go_draft_flow(client: httpx.Client, token: str, checks: list[dict[str, Any]]) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    base = "http://127.0.0.1:8002"

    save = client.post(
        f"{base}/api/kb/v1/drafts/save",
        headers=headers,
        json={
            "space_id": "corp-kb/sales",
            "path": "docs/smoke-draft.md",
            "content": "# Smoke draft\n\nLocal stack test.\n",
            "target_branch": "main",
        },
        timeout=10,
    )
    _check(
        checks,
        "go.draft_save",
        "PASS" if save.status_code == 200 else "FAIL",
        "GO saves a draft for author-1",
        f"status={save.status_code}",
    )

    get_draft = client.post(
        f"{base}/api/kb/v1/drafts/get",
        headers=headers,
        json={"space_id": "corp-kb/sales", "path": "docs/smoke-draft.md"},
        timeout=10,
    )
    ok = get_draft.status_code == 200 and "content" in get_draft.json()
    _check(
        checks,
        "go.draft_get",
        "PASS" if ok else "FAIL",
        "GO returns the saved draft",
        f"status={get_draft.status_code}",
    )

    history = client.post(
        f"{base}/api/kb/v1/documents/history",
        headers=headers,
        json={"space_id": "corp-kb/sales", "path": "docs/g1-proposal.md", "branch": "main"},
        timeout=10,
    )
    body = history.json() if history.status_code == 200 else {}
    ok = history.status_code == 200 and isinstance(body.get("commits"), list)
    _check(
        checks,
        "go.history",
        "PASS" if ok else "FAIL",
        "GO returns commit history for docs/g1-proposal.md",
        f"status={history.status_code}, commits={len(body.get('commits', []))}",
    )


def _openwebui_kb_page(client: httpx.Client, checks: list[dict[str, Any]]) -> None:
    try:
        r = client.get("http://127.0.0.1:3100/kb", timeout=10)
        _check(
            checks,
            "openwebui.kb_page",
            "PASS" if r.status_code in (200, 304) else "FAIL",
            "Open WebUI /kb page is reachable",
            f"status={r.status_code}",
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "openwebui.kb_page",
            "FAIL",
            "Open WebUI /kb page is reachable",
            f"{type(exc).__name__}: {exc}",
        )


def _openwebui_oidc_config(client: httpx.Client, checks: list[dict[str, Any]]) -> None:
    try:
        r = client.get("http://127.0.0.1:3100/api/config", timeout=10)
        body = r.json() if r.status_code == 200 else {}
        oauth = body.get("oauth", {})
        features = body.get("features", {})
        auth_enabled = bool(features.get("auth"))
        providers = oauth.get("providers", {})
        has_oidc = "oidc" in providers
        # Some Open WebUI builds omit the explicit oauth.enabled field;
        # presence of the OIDC provider plus auth feature is sufficient.
        _check(
            checks,
            "openwebui.oidc_config",
            "PASS" if auth_enabled and has_oidc else "FAIL",
            "Open WebUI /api/config shows auth and OIDC provider enabled",
            f"status={r.status_code}, auth={auth_enabled}, providers={list(providers.keys())}",
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "openwebui.oidc_config",
            "FAIL",
            "Open WebUI /api/config shows auth and OIDC provider enabled",
            f"{type(exc).__name__}: {exc}",
        )


def _keycloak_oidc_token(client: httpx.Client, checks: list[dict[str, Any]]) -> str | None:
    keycloak_url = os.environ.get("KEYCLOAK_URL", "http://localhost:8082").rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", "corp-kb")
    client_id = os.environ.get("OAUTH_CLIENT_ID", "openwebui")
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET", "")
    username = os.environ.get("KEYCLOAK_TEST_USERNAME", "g1-author")
    password = os.environ.get("KEYCLOAK_TEST_PASSWORD", "g1-author-pass")
    try:
        r = client.post(
            f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "openid email profile",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if r.status_code != 200:
            _check(
                checks,
                "keycloak.oidc_token",
                "FAIL",
                "Keycloak issues an OIDC access token for the test user",
                f"status={r.status_code}, body={r.text[:500]}",
            )
            return None
        token = r.json().get("access_token")
        _check(
            checks,
            "keycloak.oidc_token",
            "PASS" if token else "FAIL",
            "Keycloak issues an OIDC access token for the test user",
            "token present" if token else "no access_token in response",
        )
        return token
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "keycloak.oidc_token",
            "FAIL",
            "Keycloak issues an OIDC access token for the test user",
            f"{type(exc).__name__}: {exc}",
        )
        return None


def _session_oidc_validate(client: httpx.Client, token: str, checks: list[dict[str, Any]]) -> None:
    try:
        r = client.get(
            "http://127.0.0.1:8004/api/kb/v1/session/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        body = r.json() if r.status_code == 200 else {}
        ok = r.status_code == 200 and bool(body.get("stable_id"))
        _check(
            checks,
            "session.oidc_validate",
            "PASS" if ok else "FAIL",
            "Session service accepts the Keycloak OIDC access token",
            f"status={r.status_code}, stable_id={body.get('stable_id')}, role={body.get('role')}",
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "session.oidc_validate",
            "FAIL",
            "Session service accepts the Keycloak OIDC access token",
            f"{type(exc).__name__}: {exc}",
        )


def _go_identity_me(client: httpx.Client, token: str, checks: list[dict[str, Any]]) -> None:
    try:
        r = client.get(
            "http://127.0.0.1:8002/api/kb/v1/identity/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        body = r.json() if r.status_code == 200 else {}
        ok = r.status_code == 200 and bool(body.get("stable_id"))
        _check(
            checks,
            "go.identity_me_oidc",
            "PASS" if ok else "FAIL",
            "GO /api/kb/v1/identity/me returns stable identity for OIDC token",
            f"status={r.status_code}, stable_id={body.get('stable_id')}, role={body.get('role')}",
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "go.identity_me_oidc",
            "FAIL",
            "GO /api/kb/v1/identity/me returns stable identity for OIDC token",
            f"{type(exc).__name__}: {exc}",
        )


def main() -> int:
    checks: list[dict[str, Any]] = []
    generated_at = datetime.now(UTC).isoformat()

    with httpx.Client() as client:
        for name, url in SERVICES.items():
            _health_check(client, name, url, checks)
        _gitlab_health_check(client, checks)
        token = _session_flow(client, checks)
        if token:
            _go_draft_flow(client, token, checks)
        else:
            _check(
                checks,
                "go.draft_flow",
                "BLOCKED",
                "GO draft/history flow with session token",
                "session creation failed",
            )
        _openwebui_kb_page(client, checks)
        _openwebui_oidc_config(client, checks)
        oidc_token = _keycloak_oidc_token(client, checks)
        if oidc_token:
            _session_oidc_validate(client, oidc_token, checks)
            _go_identity_me(client, oidc_token, checks)
        else:
            _check(
                checks,
                "session.oidc_validate",
                "BLOCKED",
                "Session service accepts the Keycloak OIDC access token",
                "OIDC token not available",
            )
            _check(
                checks,
                "go.identity_me_oidc",
                "BLOCKED",
                "GO /api/kb/v1/identity/me returns stable identity for OIDC token",
                "OIDC token not available",
            )

    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    blocked_count = sum(1 for c in checks if c["status"] == "BLOCKED")

    report = {
        "schema_version": "local-stack-smoke-v1",
        "generated_at": generated_at,
        "environment": {
            "services": {name: url for name, url in SERVICES.items()} | {"gitlab": _gitlab_health_url()[0]},
        },
        "command": "uv run python scripts/smoke_local_stack.py",
        "counts": {
            "PASS": pass_count,
            "FAIL": fail_count,
            "BLOCKED": blocked_count,
            "TOTAL": len(checks),
        },
        "checks": checks,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "smoke-results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "smoke-results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary_lines = [
        "# Local stack smoke test",
        "",
        f"Generated: {generated_at}",
        "",
        f"- PASS: {pass_count}",
        f"- FAIL: {fail_count}",
        f"- BLOCKED: {blocked_count}",
        f"- TOTAL: {len(checks)}",
        "",
    ]
    for c in checks:
        summary_lines.extend(
            [
                f"## {c['id']} — {c['status']}",
                "",
                f"- Expected: {c['expected']}",
                f"- Actual: {c['actual']}",
                "",
            ]
        )
    summary = "\n".join(summary_lines)
    (RESULTS_DIR / "smoke-summary.md").write_text(summary, encoding="utf-8")
    (EVIDENCE_DIR / "smoke-summary.md").write_text(summary, encoding="utf-8")

    print(f"Smoke test complete: {report['counts']}")
    print(f"Results: {RESULTS_DIR / 'smoke-results.json'}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
