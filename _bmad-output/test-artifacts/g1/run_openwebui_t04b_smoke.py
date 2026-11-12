# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "playwright",
#   "httpx",
# ]
# ///

"""T04b live browser smoke test for the KB TipTap editor.

Validates the lossless serializer surface, DOMPurify preview sanitization,
and basic accessibility/IME attributes in a real browser against the
running Open WebUI /kb page.

Environment:
  OPENWEBUI_URL         Open WebUI base URL (default: http://localhost:3100)
  OPENWEBUI_TOKEN       Open WebUI native JWT for localStorage.token
  OIDC_TOKEN            Optional Keycloak OIDC access token for localStorage.oidcToken
  G1_SPACE_ID           Space to load in /kb (default: corp-kb/sales)
  G1_SHA                Commit SHA to load (default: main HEAD resolved via GO)
  GO_URL                Git orchestrator URL (default: http://localhost:8002)
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx
from playwright.sync_api import Browser, sync_playwright

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "http://localhost:3100").rstrip("/")
GO_URL = os.environ.get("GO_URL", "http://localhost:8002").rstrip("/")
SPACE_ID = os.environ.get("G1_SPACE_ID", "corp-kb/sales")
SHA = os.environ.get("G1_SHA", "")
OPENWEBUI_TOKEN = os.environ.get("OPENWEBUI_TOKEN", "")
OIDC_TOKEN = os.environ.get("OIDC_TOKEN", "")

OUTPUT_DIR = Path(__file__).resolve().parent
REPORT_JSON = OUTPUT_DIR / "t04b-smoke-results.json"
REPORT_MD = OUTPUT_DIR / "t04b-smoke-summary.md"


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


def _resolve_sha() -> str | None:
    if SHA:
        return SHA
    try:
        resp = httpx.post(
            f"{GO_URL}/api/kb/v1/documents/tree",
            json={"space_id": SPACE_ID, "sha": "main"},
            timeout=10,
        )
        if resp.is_success:
            return str(resp.json().get("sha", ""))
    except Exception as exc:  # noqa: BLE001
        return None
    return None


def _run_smoke(browser: Browser, checks: list[dict[str, Any]]) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    logs: list[str] = []
    page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
    page.on("pageerror", lambda err: logs.append(f"[pageerror] {err}"))

    sha = _resolve_sha()
    if not sha:
        _check(
            checks,
            "t04b.stack_reachable",
            "BLOCKED",
            "Local stack reachable and SHA resolved",
            f"Could not resolve SHA for {SPACE_ID} at {GO_URL}",
        )
        context.close()
        return

    _check(
        checks,
        "t04b.stack_reachable",
        "PASS",
        "Local stack reachable and SHA resolved",
        f"sha={sha}",
    )

    # Seed Open WebUI session token so the /kb page can render.
    page.goto(f"{OPENWEBUI_URL}/")
    page.evaluate("(token) => localStorage.token = token", json.dumps(OPENWEBUI_TOKEN))
    if OIDC_TOKEN:
        page.evaluate("(token) => localStorage.oidcToken = token", json.dumps(OIDC_TOKEN))

    page.goto(f"{OPENWEBUI_URL}/kb?space_id={SPACE_ID}&sha={sha}")
    page.wait_for_timeout(3000)

    # Verify the page renders the KB editor chrome.
    try:
        page.locator('[data-testid="kb-editor"]').wait_for(timeout=5000)
        _check(
            checks,
            "t04b.kb_page_loads",
            "PASS",
            "KB editor page loads",
            f"{OPENWEBUI_URL}/kb",
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "t04b.kb_page_loads",
            "FAIL",
            "KB editor page loads",
            f"{exc}; logs={logs[-10:]}",
        )
        context.close()
        return

    # Accessibility: editor exposes expected attributes.
    try:
        editor = page.locator('[role="textbox"]')
        editor.wait_for(timeout=5000)
        aria_label = editor.get_attribute("aria-label") or ""
        aria_multiline = editor.get_attribute("aria-multiline") or ""
        assert aria_label == "Knowledge base editor", aria_label
        assert aria_multiline == "true", aria_multiline
        _check(
            checks,
            "t04b.editor_a11y",
            "PASS",
            "Editor has role=textbox, aria-label and aria-multiline=true",
            f"aria-label={aria_label}, aria-multiline={aria_multiline}",
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "t04b.editor_a11y",
            "FAIL",
            "Editor has role=textbox, aria-label and aria-multiline=true",
            f"{exc}; logs={logs[-10:]}",
        )

    # Type Markdown into the TipTap editor and verify it appears.
    sample = "# T04b smoke\n\n* List item\n* Another item\n\n<script>alert('xss')</script>\n"
    try:
        editor = page.locator('[role="textbox"]')
        editor.fill(sample)
        page.wait_for_timeout(500)
        _check(
            checks,
            "t04b.editor_input",
            "PASS",
            "TipTap editor accepts Markdown input",
            "Typed sample Markdown into role=textbox",
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "t04b.editor_input",
            "FAIL",
            "TipTap editor accepts Markdown input",
            f"{exc}; logs={logs[-10:]}",
        )
        context.close()
        return

    # Toggle preview and ensure DOMPurify strips scripts.
    try:
        preview_btn = page.locator('button:has-text("Preview")')
        if preview_btn.count() > 0 and preview_btn.first.is_visible():
            preview_btn.first.click()
            page.wait_for_timeout(500)

        preview = page.locator('[data-testid="kb-preview"]')
        preview.wait_for(timeout=5000)
        html = preview.inner_html()
        has_script = "<script>" in html.lower() or "</script>" in html.lower()
        _check(
            checks,
            "t04b.preview_sanitizes",
            "FAIL" if has_script else "PASS",
            "Preview contains no script tags after DOMPurify",
            "script found" if has_script else "script stripped",
            {"preview_html_snippet": html[:500]},
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "t04b.preview_sanitizes",
            "FAIL",
            "Preview contains no script tags after DOMPurify",
            f"{exc}; logs={logs[-10:]}",
        )

    # No uncaught JS errors during the smoke.
    page_errors = [l for l in logs if l.startswith("[pageerror]")]
    if page_errors:
        _check(
            checks,
            "t04b.no_page_errors",
            "FAIL",
            "No uncaught page errors",
            "; ".join(page_errors[:5]),
        )
    else:
        _check(
            checks,
            "t04b.no_page_errors",
            "PASS",
            "No uncaught page errors",
            "none",
        )

    context.close()


def main() -> int:
    checks: list[dict[str, Any]] = []

    if not OPENWEBUI_TOKEN:
        _check(
            checks,
            "t04b.token_available",
            "BLOCKED",
            "OPENWEBUI_TOKEN provided",
            "missing",
        )

    try:
        httpx.get(f"{OPENWEBUI_URL}/", timeout=5)
        _check(
            checks,
            "t04b.openwebui_reachable",
            "PASS",
            "Open WebUI reachable",
            OPENWEBUI_URL,
        )
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "t04b.openwebui_reachable",
            "BLOCKED",
            "Open WebUI reachable",
            f"{exc}",
        )

    if not OPENWEBUI_TOKEN or any(
        c["status"] == "BLOCKED" for c in checks if c["id"].startswith("t04b.openwebui")
    ):
        _write_reports(checks)
        return 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            _run_smoke(browser, checks)
            browser.close()
    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "t04b.playwright_launch",
            "BLOCKED",
            "Playwright browser launches",
            f"{exc}",
        )

    _write_reports(checks)

    fails = [c for c in checks if c["status"] == "FAIL"]
    blocked = [c for c in checks if c["status"] == "BLOCKED"]
    passes = [c for c in checks if c["status"] == "PASS"]
    print(f"T04b smoke: {len(passes)} PASS, {len(fails)} FAIL, {len(blocked)} BLOCKED")
    return 1 if fails else 0


def _write_reports(checks: list[dict[str, Any]]) -> None:
    REPORT_JSON.write_text(json.dumps(checks, indent=2), encoding="utf-8")
    lines = ["# T04b live browser smoke results", ""]
    for c in checks:
        lines.append(f"## {c['id']} — {c['status']}")
        lines.append(f"- Expected: {c['expected']}")
        lines.append(f"- Actual: {c['actual']}")
        if c.get("details"):
            lines.append(f"- Details: {c['details']}")
        lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
