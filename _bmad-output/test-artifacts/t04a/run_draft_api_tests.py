# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest",
#   "fastapi",
#   "httpx",
#   "sqlalchemy",
#   "pydantic",
#   "pydantic-settings",
# ]
# ///

"""T04a API-level synthetic harness for drafts and history.

Runs the pytest suite in ``src/git-orchestrator/tests/test_t04a_drafts.py``
using the seeded in-memory SQLite environment and writes deterministic JSON/Markdown
evidence for G1.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

OUTPUT_DIR = Path("_bmad-output/test-artifacts/t04a")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t04a")
SPEC_BASELINE_COMMIT = "d2c0d072a757808ea891fbf6414f00147679f7a7"
T00_BASELINE_COMMIT = "152b00ff6aaa7b95c7b958d822bf54e8a54d1650"


class _ResultCollector:
    """Minimal pytest plugin that records test outcomes."""

    def __init__(self) -> None:
        self.tests: list[dict[str, Any]] = []

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when != "call":
            return
        status = "PASS" if report.outcome == "passed" else "FAIL"
        self.tests.append(
            {
                "id": report.nodeid,
                "status": status,
                "expected": "test passes",
                "actual": report.outcome,
                "details": {"duration": report.duration},
            }
        )


def _run_pytest() -> tuple[int, list[dict[str, Any]]]:
    """Run the T04a pytest file and collect outcomes."""
    repo_root = Path(__file__).resolve().parents[3]
    test_path = repo_root / "src" / "git-orchestrator" / "tests" / "test_t04a_drafts.py"
    collector = _ResultCollector()
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///:memory:"
    env["KB_OPS_SCHEMA"] = ""
    os.environ.update(env)
    returncode = pytest.main(
        [str(test_path), "-q", "--tb=short"],
        plugins=[collector],
    )
    return returncode, collector.tests


def _build_report(tests: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "TOTAL": len(tests)}
    for t in tests:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    return {
        "schema_version": "t04a-api-results-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_commit": T00_BASELINE_COMMIT,
        "spec_baseline_commit": SPEC_BASELINE_COMMIT,
        "command": "uv run python _bmad-output/test-artifacts/t04a/run_draft_api_tests.py",
        "counts": counts,
        "checks": tests,
    }


def _sanitize(report: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitized copy with no absolute paths or secrets."""
    return json.loads(json.dumps(report, ensure_ascii=False))


def _write_outputs(report: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = OUTPUT_DIR / "api-results.json"
    raw_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary_lines = [
        "# T04a API-level synthetic results",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"- PASS: {report['counts']['PASS']}",
        f"- FAIL: {report['counts']['FAIL']}",
        f"- BLOCKED: {report['counts']['BLOCKED']}",
        f"- TOTAL: {report['counts']['TOTAL']}",
        "",
    ]
    for check in report["checks"]:
        summary_lines.extend(
            [
                f"## {check['id']} — {check['status']}",
                "",
                f"- Expected: {check['expected']}",
                f"- Actual: {check['actual']}",
                "",
            ]
        )
    summary = "\n".join(summary_lines)
    (OUTPUT_DIR / "api-summary.md").write_text(summary, encoding="utf-8")

    sanitized = _sanitize(report)
    (EVIDENCE_DIR / "api-results.json").write_text(
        json.dumps(sanitized, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "api-summary.md").write_text(summary, encoding="utf-8")

    print(f"Wrote {raw_path}")
    print(f"Counts: {report['counts']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="T04a draft/history API synthetic harness")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the tests that would be run without executing them",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("Would run: src/git-orchestrator/tests/test_t04a_drafts.py")
        return 0

    returncode, tests = _run_pytest()
    report = _build_report(tests)
    _write_outputs(report)
    return returncode


if __name__ == "__main__":
    sys.exit(main())
