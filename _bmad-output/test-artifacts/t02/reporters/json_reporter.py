"""Deterministic report envelope builder for T02 document tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Check:
    """One document-test check result."""

    id: str
    scenario_id: str
    status: str  # PASS / FAIL / BLOCKED
    expected: str
    actual: str
    input_sha256: str | None = None
    fixture_path: str | None = None
    rerun_cmd: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class ReportBuilder:
    """Assemble deterministic document-results.json envelope."""

    def __init__(
        self,
        baseline_commit: str,
        spec_baseline_commit: str,
        contracts_version: str,
        output_dir: Path,
    ) -> None:
        self.baseline_commit = baseline_commit
        self.spec_baseline_commit = spec_baseline_commit
        self.contracts_version = contracts_version
        self.output_dir = output_dir
        self.checks: list[Check] = []

    def add(self, check: Check) -> None:
        self.checks.append(check)

    def build(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        checks = [self._check_to_dict(c) for c in self.checks]
        report = {
            "schema_version": "t02-document-results-v1",
            "generated_at": now,
            "baseline_commit": self.baseline_commit,
            "spec_baseline_commit": self.spec_baseline_commit,
            "contracts_version": self.contracts_version,
            "environment": {
                "sandbox": "synthetic_local_no_gitlab",
                "git_lab_available": False,
                "idp_available": False,
                "ci_available": False,
                "hoster_available": False,
                "pinned_toolchain": {
                    "open_webui": "v0.13.0",
                    "open_webui_commit": "c38885a1a737da4968f157092f304f3b5481d0bf",
                    "gitlab_ce": "19.5.3-ce.0",
                    "postgresql": "18.6",
                    "pgvector": "0.8.7",
                    "python": "3.12.13",
                    "uv": "0.11.13",
                },
            },
            "secrets_included": False,
            "command": "uv run python _bmad-output/test-artifacts/t02/run_document_tests.py",
            "rerun_cmd": "uv run python _bmad-output/test-artifacts/t02/run_document_tests.py",
            "counts": self._counts(),
            "checks": checks,
        }
        return report

    @staticmethod
    def _check_to_dict(check: Check) -> dict[str, Any]:
        return {
            "id": check.id,
            "scenario_id": check.scenario_id,
            "status": check.status,
            "expected": check.expected,
            "actual": check.actual,
            "input_sha256": check.input_sha256,
            "fixture_path": check.fixture_path,
            "rerun_cmd": check.rerun_cmd,
            "details": check.details,
        }

    def _counts(self) -> dict[str, int]:
        counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0}
        for c in self.checks:
            counts[c.status] = counts.get(c.status, 0) + 1
        fail_expected = sum(
            1
            for c in self.checks
            if c.status == "FAIL" and c.details.get("expected_negative") is True
        )
        fail_unexpected = counts["FAIL"] - fail_expected
        return {
            "PASS": counts["PASS"],
            "FAIL": counts["FAIL"],
            "FAIL_EXPECTED": fail_expected,
            "FAIL_UNEXPECTED": fail_unexpected,
            "BLOCKED": counts["BLOCKED"],
        }

    def write_json(self, path: Path) -> None:
        report = self.build()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))
