# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "fastapi",
#   "httpx",
#   "sqlalchemy",
#   "psycopg",
#   "pydantic",
#   "pydantic-settings",
#   "pytest",
# ]
# ///

"""Standalone runner for the synthetic G1 API fault-matrix tests.

This script executes ``src/git-orchestrator/tests/test_g1_fault_matrix.py``
using pytest's programmatic API, collects the results, and writes JSON/Markdown
reports under ``_bmad-output/test-artifacts/g1/``. A sanitized Markdown summary
is also written to ``specs/corporate-kb/evidence/g1/``.

The harness uses only synthetic fixtures and the stub GitLab adapter. Live
GitLab acceptance is explicitly optional and remains gated by
``G1_ALLOW_DESTRUCTIVE_RESET=1``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

OUTPUT_DIR = Path(__file__).resolve().parent
REPORT_JSON = OUTPUT_DIR / "g1-fault-matrix-results.json"
REPORT_MD = OUTPUT_DIR / "g1-fault-matrix-summary.md"
EVIDENCE_DIR = Path(__file__).resolve().parents[3] / "specs" / "corporate-kb" / "evidence" / "g1"
EVIDENCE_MD = EVIDENCE_DIR / "g1-fault-matrix-evidence.md"

TEST_FILE = Path(__file__).resolve().parents[3] / "src" / "git-orchestrator" / "tests" / "test_g1_fault_matrix.py"


class _FaultMatrixPlugin:
    """Pytest plugin that records a PASS/FAIL result per test case."""

    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when != "call":
            return
        nodeid = report.nodeid
        # Convert nodeid to a stable check id: file::Class::test_name -> Class.test_name
        check_id = nodeid.split("::", 1)[-1].replace("::", ".")
        status = "PASS" if report.outcome == "passed" else "FAIL"
        self.checks.append(
            {
                "id": check_id,
                "status": status,
                "expected": "test passes",
                "actual": report.outcome,
                "details": {"longrepr": str(report.longrepr) if report.longrepr else ""},
            }
        )


def _run_tests() -> tuple[list[dict[str, Any]], int]:
    plugin = _FaultMatrixPlugin()
    # Run the dedicated test file with pytest's programmatic API.
    exit_code = pytest.main(
        [
            str(TEST_FILE),
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:randomly",
        ],
        plugins=[plugin],
    )
    return plugin.checks, int(exit_code)


def _render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "# G1 API Fault-Matrix Synthetic Evidence",
        "",
        f"- **Generated:** {report['generated_at']}",
        f"- **Environment:** {report['environment']['sandbox']}",
        f"- **Command:** `{report['command']}`",
        "",
        "## Scope",
        "",
        "This report covers the synthetic closure of G1 API fault-matrix gates ",
        "A05–A10 / A27–A30 plus concurrency/idempotency scenarios. ",
        "It exercises invalid state transitions, actor mismatches, self-approval, ",
        "idempotency violations, concurrent decision races, malformed payloads, ",
        "reject/cancel/supersede semantics, and merge recovery barriers against ",
        "the GO FastAPI TestClient with an in-memory stub GitLab adapter.",
        "",
        "Live GitLab/PostgreSQL acceptance is **not** covered here; it remains ",
        "optional and requires ``G1_ALLOW_DESTRUCTIVE_RESET=1``.",
        "",
        "## Counts",
        "",
        f"- PASS: {counts['PASS']}",
        f"- FAIL: {counts['FAIL']}",
        f"- TOTAL: {counts['TOTAL']}",
        "",
        "## Checks",
        "",
        "| ID | Status | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for c in report["checks"]:
        actual_short = (c["actual"] or "")[:120].replace("|", "\\|")
        details = c.get("details", {})
        detail_tail = (details.get("longrepr") or "")[:120].replace("|", "\\|").replace("\n", " ")
        actual_cell = f"{actual_short} {detail_tail}".strip()
        lines.append(
            f"| {c['id']} | {c['status']} | {c['expected']} | {actual_cell} |"
        )
    lines.append("")
    lines.append("## Rerun instructions")
    lines.append("")
    lines.append(f"```bash\n{report['command']}\n```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    generated_at = datetime.now(UTC).isoformat()
    checks, exit_code = _run_tests()

    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")

    report = {
        "schema_version": "g1-fault-matrix-v1",
        "generated_at": generated_at,
        "environment": {
            "sandbox": "synthetic_stub_gitlab",
            "database": "sqlite_in_memory",
            "pinned_toolchain": {
                "open_webui": "v0.13.0",
                "open_webui_commit": "c38885a1a737da4968f157092f304f3b5481d0bf",
                "python": "3.12.13",
                "uv": "0.11.13",
            },
        },
        "sensitive_data_included": False,
        "command": "uv run python _bmad-output/test-artifacts/g1/run_g1_fault_matrix.py",
        "live_gitlab_acceptance": "optional; requires G1_ALLOW_DESTRUCTIVE_RESET=1",
        "counts": {
            "PASS": pass_count,
            "FAIL": fail_count,
            "TOTAL": len(checks),
        },
        "checks": checks,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    REPORT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md = _render_markdown(report)
    REPORT_MD.write_text(md, encoding="utf-8")
    EVIDENCE_MD.write_text(md, encoding="utf-8")

    print(f"Wrote {REPORT_JSON}")
    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {EVIDENCE_MD}")
    print(f"Counts: PASS={pass_count}, FAIL={fail_count}, TOTAL={len(checks)}")

    # Propagate pytest exit code unless there were failures, in which case 1.
    return 1 if fail_count > 0 else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
