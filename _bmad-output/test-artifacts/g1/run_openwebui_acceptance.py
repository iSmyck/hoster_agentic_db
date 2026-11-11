# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "playwright",
#   "httpx",
#   "python-dotenv",
#   "sqlalchemy",
#   "alembic",
#   "psycopg",
# ]
# ///

"""Open WebUI native KB editor acceptance test (T04a/T04b live)."""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from playwright.sync_api import Browser, Page, expect, sync_playwright
from sqlalchemy.engine import make_url

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

OUTPUT_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = Path(__file__).resolve().parents[3] / "specs" / "corporate-kb" / "evidence" / "g1"
REPORT_JSON = OUTPUT_DIR / "g1-openwebui-results.json"
SUMMARY_MD = OUTPUT_DIR / "g1-openwebui-summary.md"
EVIDENCE_JSON = EVIDENCE_DIR / "g1-openwebui-results.json"
EVIDENCE_MD = EVIDENCE_DIR / "g1-openwebui-summary.md"

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "http://localhost:5050")
GO_URL = os.environ.get("GO_URL", "http://localhost:8002")
SPACE_ID = os.environ.get("G1_SPACE_ID", "corp-kb/sales")
TARGET_BRANCH = os.environ.get("G1_TARGET_BRANCH", "main")

RUN_ID = uuid.uuid4().hex[:12]
ADMIN_EMAIL = f"g1-admin-{RUN_ID}@hoster.test"
ADMIN_PASSWORD = secrets.token_urlsafe(24)
AUTHOR_EMAIL = f"g1-author-{RUN_ID}@hoster.test"
AUTHOR_PASSWORD = secrets.token_urlsafe(24)
APPROVER_EMAIL = f"g1-approver-{RUN_ID}@hoster.test"
APPROVER_PASSWORD = secrets.token_urlsafe(24)


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


def _dismiss_onboarding(page: Page) -> None:
    get_started = page.locator('button[aria-label="Get started"]')
    if get_started.count() > 0:
        get_started.first.click()
        page.wait_for_timeout(1000)
    close = page.locator('div[role="dialog"] button[aria-label="Close"]')
    if close.count() > 0 and close.first.is_visible():
        close.first.click()
        page.wait_for_timeout(500)


def _signin_via_api(email: str, password: str) -> str | None:
    try:
        r = httpx.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": email, "password": password},
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("token")
        return None
    except Exception:  # noqa: BLE001
        return None


def _signup_via_api(email: str, password: str, name: str) -> str | None:
    token = _signin_via_api(email, password)
    if token:
        return token
    try:
        r = httpx.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signup",
            json={"email": email, "password": password, "name": name},
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("token")
        return None
    except Exception:  # noqa: BLE001
        return None


def _admin_session_token() -> str | None:
    configured = os.environ.get("OPENWEBUI_ADMIN_TOKEN")
    if configured:
        return configured
    email = os.environ.get("OPENWEBUI_ADMIN_EMAIL")
    password = os.environ.get("OPENWEBUI_ADMIN_PASSWORD")
    if email and password:
        return _signin_via_api(email, password)
    return _signup_via_api(ADMIN_EMAIL, ADMIN_PASSWORD, "G1 Admin")


def _create_user_via_api(
    admin_token: str, email: str, password: str, name: str, role: str = "user"
) -> str | None:
    token = _signin_via_api(email, password)
    if token:
        return token
    try:
        r = httpx.post(
            f"{OPENWEBUI_URL}/api/v1/auths/add",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json={"email": email, "password": password, "name": name, "role": role},
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("token")
        return None
    except Exception:  # noqa: BLE001
        return None


def _wait_for_status(page: Page, marker: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        text = page.locator("#kb-status").text_content() or ""
        if marker in text or "ERROR:" in text:
            return
        time.sleep(0.5)


def _extract_json_value(text: str, key: str) -> str | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and key in obj:
                value = obj[key]
                return str(value) if value is not None else None
        except json.JSONDecodeError:
            continue
    return None


def _gitlab_project_url(space_id: str) -> str:
    encoded = space_id.replace("/", "%2F")
    return f"{os.environ.get('GO_GITLAB_URL', 'http://localhost:8081')}/api/v4/projects/{encoded}"


def _gitlab_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {os.environ['GO_GITLAB_TOKEN']}"}


def _verify_merge_commit(
    merge_sha: str, expected_base: str, expected_proposal: str
) -> dict[str, Any]:
    url = f"{_gitlab_project_url(SPACE_ID)}/repository/commits/{merge_sha}"
    r = httpx.get(url, headers=_gitlab_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    parents = data.get("parent_ids", [])
    return {
        "parents": parents,
        "first_parent_matches_base": bool(parents) and parents[0] == expected_base,
        "second_parent_matches_proposal": len(parents) >= 2 and parents[1] == expected_proposal,
        "message": data.get("message", ""),
    }


def _wait_for_mergeable(proposal_sha: str, timeout: float = 45.0) -> None:
    source_branch = f"proposal/{proposal_sha[:8]}"
    url = f"{_gitlab_project_url(SPACE_ID)}/merge_requests"
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = httpx.get(
            url,
            headers=_gitlab_headers(),
            params={"source_branch": source_branch, "state": "opened"},
            timeout=30,
        )
        response.raise_for_status()
        requests = response.json()
        if requests:
            mr_url = f"{url}/{requests[0]['iid']}"
            mr_response = httpx.get(mr_url, headers=_gitlab_headers(), timeout=30)
            mr_response.raise_for_status()
            mr = mr_response.json()
            if (
                mr.get("detailed_merge_status") == "mergeable"
                or mr.get("merge_status") == "can_be_merged"
            ):
                return
        time.sleep(0.5)
    raise RuntimeError(f"MR for {source_branch} did not become mergeable within {timeout}s")


def _verify_decision_tag(decision_id: str, expected_proposal_sha: str) -> dict[str, Any]:
    tag_name = f"kb-decisions/{decision_id}"
    url = f"{_gitlab_project_url(SPACE_ID)}/repository/tags/{tag_name.replace('/', '%2F')}"
    r = httpx.get(url, headers=_gitlab_headers(), timeout=30)
    if r.status_code == 404:
        return {"found": False}
    r.raise_for_status()
    data = r.json()
    target = str(data.get("commit", {}).get("id", ""))
    return {
        "found": True,
        "target_matches_proposal_sha": target == expected_proposal_sha,
        "protected": bool(data.get("protected")),
    }


def _run_author_flow(
    browser: Browser, token: str, checks: list[dict[str, Any]]
) -> dict[str, Any] | None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.goto(f"{OPENWEBUI_URL}/")
    page.evaluate(f"() => localStorage.token = '{token}'")
    page.goto(f"{OPENWEBUI_URL}/kb")
    page.wait_for_timeout(2000)
    _dismiss_onboarding(page)
    expect(page.locator("h1")).to_contain_text("Managed KB Editor")
    _check(checks, "openwebui.kb_page_loads", "PASS", "KB editor page loads", f"{OPENWEBUI_URL}/kb")

    file_path = f"docs/g1-openwebui-{RUN_ID}.md"
    content = f"# G1 Open WebUI proposal {RUN_ID}\n\nNative editor change.\n"
    page.locator("#kb-path").fill(file_path)
    page.locator("#kb-content").fill(content)

    submit_btn = page.locator("button:has-text('1. Submit proposal')")
    try:
        if submit_btn.count() == 0:
            raise RuntimeError("Submit proposal button not found")
        if submit_btn.is_disabled():
            raise RuntimeError("Submit proposal button is disabled")
        submit_btn.click()
    except Exception as exc:  # noqa: BLE001
        try:
            status_text = page.locator("#kb-status").text_content() or ""
        except Exception:  # noqa: BLE001
            status_text = ""
        _check(
            checks,
            "openwebui.author_submit",
            "FAIL",
            "author submits proposal via Open WebUI",
            f"{exc}; status={status_text[:500]}",
        )
        context.close()
        return None
    _wait_for_status(page, "proposal_id")
    status_text = page.locator("#kb-status").text_content() or ""
    proposal_id = _extract_json_value(status_text, "proposal_id")
    proposal_sha = _extract_json_value(status_text, "proposal_sha")
    base_sha = _extract_json_value(status_text, "base_sha")
    if not proposal_id:
        _check(
            checks,
            "openwebui.author_submit",
            "FAIL",
            "author submits proposal via Open WebUI",
            status_text[:1000],
        )
        context.close()
        return None
    _check(
        checks,
        "openwebui.author_submit",
        "PASS",
        "author submits proposal via Open WebUI",
        f"proposal_id={proposal_id}",
    )

    # The author session cannot approve its own proposal.
    page.locator("button:has-text('2. Record decision')").click()
    _wait_for_status(page, "ERROR:")
    status_text = page.locator("#kb-status").text_content() or ""
    denied = "APPROVER_REQUIRED" in status_text
    _check(
        checks,
        "openwebui.author_cannot_approve",
        "PASS" if denied else "FAIL",
        "author session cannot record an approval",
        status_text[-500:],
    )
    context.close()
    if not denied:
        return None
    return {
        "proposal_id": proposal_id,
        "proposal_sha": proposal_sha,
        "base_sha": base_sha,
        "file_path": file_path,
    }


def _run_approver_flow(
    browser: Browser, token: str, flow: dict[str, Any], checks: list[dict[str, Any]]
) -> dict[str, Any] | None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.goto(f"{OPENWEBUI_URL}/")
    page.evaluate(f"() => localStorage.token = '{token}'")
    page.goto(f"{OPENWEBUI_URL}/kb?proposal={flow['proposal_id']}")
    page.wait_for_timeout(2500)
    _dismiss_onboarding(page)

    page.locator("button:has-text('2. Record decision')").click()
    _wait_for_status(page, "decision_id")
    status_text = page.locator("#kb-status").text_content() or ""
    decision_id = _extract_json_value(status_text, "decision_id")
    if not decision_id:
        _check(
            checks,
            "openwebui.approver_decision",
            "FAIL",
            "approver records decision in independent session",
            status_text[-1000:],
        )
        context.close()
        return None
    _check(
        checks,
        "openwebui.approver_decision",
        "PASS",
        "approver records decision in independent session",
        f"decision_id={decision_id}",
    )

    _wait_for_mergeable(flow["proposal_sha"])
    page.locator("button:has-text('3. Merge')").click()
    _wait_for_status(page, "merge_sha")
    status_text = page.locator("#kb-status").text_content() or ""
    merge_sha = _extract_json_value(status_text, "merge_sha")
    if not merge_sha:
        _check(
            checks,
            "openwebui.approver_merge",
            "FAIL",
            "approver executes merge in independent session",
            status_text[-1000:],
        )
        context.close()
        return None
    _check(
        checks,
        "openwebui.approver_merge",
        "PASS",
        "approver executes merge in independent session",
        f"merge_sha={merge_sha}",
    )
    context.close()
    return {**flow, "decision_id": decision_id, "merge_sha": merge_sha}


def _validate_reset_target(database_url: str, schema: str) -> None:
    import re

    if os.environ.get("G1_ALLOW_DESTRUCTIVE_RESET") != "1":
        raise RuntimeError("set G1_ALLOW_DESTRUCTIVE_RESET=1 for the disposable G1 schema")
    if not re.fullmatch(r"kb_ops_g1_test(_[a-z0-9_]+)?", schema):
        raise RuntimeError("GO_KB_OPS_SCHEMA must be a dedicated kb_ops_g1_test* schema")
    if make_url(database_url).host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("destructive G1 reset is allowed only on localhost")


def _safe_dsn(database_url: str) -> str:
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(database_url)
    return urlunsplit(
        (parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, parts.query, parts.fragment)
    )


def _security_api_checks(author_token: str, checks: list[dict[str, Any]]) -> None:
    payload = {
        "space_id": SPACE_ID,
        "branch": TARGET_BRANCH,
        "file_path": f"docs/g1-prepare-replay-{RUN_ID}.md",
        "content": "# Prepare replay\n",
        "idempotency_key": f"g1-prepare-{RUN_ID}",
    }
    unauthenticated = httpx.post(f"{GO_URL}/api/g1-editor/prepare-branch", json=payload, timeout=30)
    _check(
        checks,
        "security.prepare_requires_session",
        "PASS" if unauthenticated.status_code == 401 else "FAIL",
        "prepare-branch rejects unauthenticated writes",
        f"status={unauthenticated.status_code}",
    )

    headers = {"Authorization": f"Bearer {author_token}"}
    forbidden = httpx.post(
        f"{GO_URL}/api/g1-editor/prepare-branch",
        headers=headers,
        json={**payload, "file_path": ".gitlab-ci.yml", "idempotency_key": f"g1-ci-{RUN_ID}"},
        timeout=30,
    )
    _check(
        checks,
        "security.prepare_rejects_ci_path",
        "PASS" if forbidden.status_code in {400, 403} else "FAIL",
        "prepare-branch rejects CI/service paths",
        f"status={forbidden.status_code}",
    )

    first = httpx.post(
        f"{GO_URL}/api/g1-editor/prepare-branch", headers=headers, json=payload, timeout=60
    )
    second = httpx.post(
        f"{GO_URL}/api/g1-editor/prepare-branch", headers=headers, json=payload, timeout=60
    )
    same_sha = (
        first.status_code == 200
        and second.status_code == 200
        and first.json().get("proposal_sha") == second.json().get("proposal_sha")
        and first.json().get("base_sha") == second.json().get("base_sha")
    )
    _check(
        checks,
        "security.prepare_replay_idempotent",
        "PASS" if same_sha else "FAIL",
        "prepare retry returns identical proposal/base SHA",
        f"first={first.status_code}:{first.text[:200]}, second={second.status_code}:{second.text[:200]}",
    )


def _write_report(checks: list[dict[str, Any]], generated_at: str, db_url: str) -> int:
    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    blocked_count = sum(1 for c in checks if c["status"] == "BLOCKED")

    report = {
        "schema_version": "g1-openwebui-acceptance-v1",
        "generated_at": generated_at,
        "environment": {
            "openwebui_url": OPENWEBUI_URL,
            "go_url": GO_URL,
            "space_id": SPACE_ID,
            "database": _safe_dsn(db_url) if db_url else "unknown",
        },
        "sensitive_data_included": False,
        "command": "uv run python _bmad-output/test-artifacts/g1/run_openwebui_acceptance.py",
        "counts": {
            "PASS": pass_count,
            "FAIL": fail_count,
            "BLOCKED": blocked_count,
            "TOTAL": len(checks),
        },
        "checks": checks,
    }

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
        )
        EVIDENCE_JSON.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
        )

        summary = f"# G1 Open WebUI acceptance summary\n\nGenerated: {generated_at}\n\n"
        summary += f"- PASS: {pass_count}\n- FAIL: {fail_count}\n- BLOCKED: {blocked_count}\n- TOTAL: {len(checks)}\n\n"
        for c in checks:
            summary += f"## {c['id']} — {c['status']}\n\n- Expected: {c['expected']}\n- Actual: {c['actual']}\n\n"
        SUMMARY_MD.write_text(summary, encoding="utf-8")
        EVIDENCE_MD.write_text(summary, encoding="utf-8")
    except OSError as exc:
        print(f"Failed to write acceptance report: {exc}", file=sys.stderr)
        return 1

    print(f"Counts: {report['counts']}")
    return 0 if fail_count == 0 else 1


def main() -> int:
    checks: list[dict[str, Any]] = []
    generated_at = datetime.now(UTC).isoformat()
    db_url = os.environ.get("GO_DATABASE_URL") or os.environ.get("DATABASE_URL") or ""

    print("Checking GO health...", flush=True)
    # Check GO health.
    try:
        r = httpx.get(f"{GO_URL}/health", timeout=5)
        _check(
            checks,
            "precondition.go_health",
            "PASS" if r.status_code == 200 else "FAIL",
            "GO health endpoint returns 200",
            f"status={r.status_code}",
        )
    except Exception as exc:  # noqa: BLE001
        _check(checks, "precondition.go_health", "FAIL", "GO health endpoint returns 200", str(exc))
        return _write_report(checks, generated_at, db_url)

    # Reset kb_ops schema and run migrations for a clean state.
    try:
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import create_engine, text

        if not db_url:
            raise RuntimeError("set GO_DATABASE_URL or DATABASE_URL for the G1 harness")
        schema = os.environ.get("GO_KB_OPS_SCHEMA", "kb_ops_g1_test")
        _validate_reset_target(db_url, schema)
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        engine.dispose()

        os.environ["DATABASE_URL"] = db_url
        os.environ["GO_KB_OPS_SCHEMA"] = schema
        alembic_cfg = Config()
        alembic_cfg.set_main_option(
            "script_location",
            str(Path(__file__).resolve().parents[3] / "src" / "git-orchestrator" / "migrations"),
        )
        alembic_cfg.set_main_option("version_path_separator", "os")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")
        _check(
            checks,
            "precondition.schema_reset",
            "PASS",
            "kb_ops schema reset and migrations applied",
            f"schema={schema}",
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "precondition.schema_reset",
            "FAIL",
            "kb_ops schema reset and migrations applied",
            f"{type(exc).__name__}: {exc}",
        )
        return _write_report(checks, generated_at, db_url)

    print("Starting Playwright...", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        print("Obtaining admin session...", flush=True)
        admin_token = _admin_session_token()
        if not admin_token:
            _check(
                checks,
                "openwebui.admin_token",
                "FAIL",
                "admin token available",
                "set OPENWEBUI_ADMIN_TOKEN or admin credentials",
            )
            browser.close()
            return _write_report(checks, generated_at, db_url)
        _check(checks, "openwebui.admin_token", "PASS", "admin token available", "token present")

        author_token = _create_user_via_api(
            admin_token, AUTHOR_EMAIL, AUTHOR_PASSWORD, "G1 Author", role="user"
        )
        approver_token = _create_user_via_api(
            admin_token, APPROVER_EMAIL, APPROVER_PASSWORD, "G1 Approver", role="admin"
        )
        print(
            f"User creation: author={bool(author_token)}, approver={bool(approver_token)}",
            flush=True,
        )
        if not author_token or not approver_token:
            _check(
                checks,
                "openwebui.create_users",
                "FAIL",
                "random per-run author and approver created",
                f"author={bool(author_token)}, approver={bool(approver_token)}",
            )
            browser.close()
            return _write_report(checks, generated_at, db_url)
        _check(
            checks,
            "openwebui.create_users",
            "PASS",
            "random per-run author and approver created",
            "both tokens present",
        )
        _security_api_checks(author_token, checks)
        print("Security API checks completed", flush=True)

        flow = _run_author_flow(browser, author_token, checks)
        print(f"Author flow: {bool(flow)}", flush=True)
        if flow is None:
            browser.close()
            return _write_report(checks, generated_at, db_url)
        flow = _run_approver_flow(browser, approver_token, flow, checks)
        if flow is None:
            browser.close()
            return _write_report(checks, generated_at, db_url)
        _check(
            checks,
            "openwebui.independent_sessions",
            "PASS",
            "author and approver use independent browser sessions",
            "two isolated browser contexts",
        )

        # Verify GitLab-side evidence.
        proof = _verify_merge_commit(flow["merge_sha"], flow["base_sha"], flow["proposal_sha"])
        _check(
            checks,
            "openwebui.merge_parentage",
            "PASS"
            if proof["first_parent_matches_base"] and proof["second_parent_matches_proposal"]
            else "FAIL",
            "merge commit parents equal base_sha and proposal_sha",
            f"parents={proof['parents']}",
            proof,
        )
        _check(
            checks,
            "openwebui.merge_trailers",
            "PASS" if str(flow["decision_id"]) in proof["message"] else "FAIL",
            "merge commit contains Decision-ID trailer",
            proof["message"],
            proof,
        )

        tag_proof = _verify_decision_tag(flow["decision_id"], flow["proposal_sha"])
        _check(
            checks,
            "openwebui.decision_tag",
            "PASS"
            if tag_proof.get("found")
            and tag_proof.get("target_matches_proposal_sha")
            and tag_proof.get("protected")
            else "FAIL",
            "protected annotated tag exists on proposal_sha",
            f"found={tag_proof.get('found')}, target_matches={tag_proof.get('target_matches_proposal_sha')}, protected={tag_proof.get('protected')}",
            tag_proof,
        )

        file_url = f"{_gitlab_project_url(SPACE_ID)}/repository/files/{flow['file_path'].replace('/', '%2F')}/raw"
        r = httpx.get(
            file_url, headers=_gitlab_headers(), params={"ref": TARGET_BRANCH}, timeout=30
        )
        _check(
            checks,
            "openwebui.merged_file_visible",
            "PASS" if r.status_code == 200 else "FAIL",
            "merged page is readable on target branch",
            f"status={r.status_code}, len={len(r.text)}",
        )

        browser.close()

    return _write_report(checks, generated_at, db_url)


if __name__ == "__main__":
    raise SystemExit(main())
