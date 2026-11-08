"""Unit tests for the reference reporter and sanitizer (T01 harness)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def test_report_builder_empty(t01_modules: Any) -> None:
    rb = t01_modules.json_reporter.ReportBuilder(
        baseline_commit="abc123defabc123defabc123defabc123defabcd",
        contracts_version="t01-contracts-v1",
        output_dir=Path("/tmp"),
    )
    report = rb.build()

    assert report["schema_version"] == "t01-contract-results-v1"
    assert report["baseline_commit"] == "abc123defabc123defabc123defabc123defabcd"
    assert report["contracts_version"] == "t01-contracts-v1"
    assert report["counts"] == {
        "PASS": 0,
        "FAIL": 0,
        "BLOCKED": 0,
        "NOT_EXECUTED": 0,
    }
    assert "generated_at" in report
    assert "environment" in report
    assert report["environment"]["sandbox"] == "synthetic_local_no_gitlab"


def test_report_builder_counts(t01_modules: Any) -> None:
    rb = t01_modules.json_reporter.ReportBuilder(
        baseline_commit="abc123defabc123defabc123defabc123defabcd",
        contracts_version="v1",
        output_dir=Path("/tmp"),
    )
    Check = t01_modules.json_reporter.Check
    rb.add(Check("c1", "cf01", "PASS", "p", "p"))
    rb.add(Check("c2", "cf02", "FAIL", "p", "f"))
    rb.add(Check("c3", "cf03", "BLOCKED", "p", "b"))
    rb.add(Check("c4", "cf04", "NOT_EXECUTED", "p", "n"))

    counts = rb.build()["counts"]
    assert counts == {"PASS": 1, "FAIL": 1, "BLOCKED": 1, "NOT_EXECUTED": 1}


def test_report_builder_deterministic(t01_modules: Any, tmp_path: Path) -> None:
    rb = t01_modules.json_reporter.ReportBuilder(
        baseline_commit="abc123defabc123defabc123defabc123defabcd",
        contracts_version="v1",
        output_dir=tmp_path,
    )
    rb.add(
        t01_modules.json_reporter.Check(
            "c1", "cf01", "PASS", "expected text", "actual text"
        )
    )

    p1 = tmp_path / "r1.json"
    p2 = tmp_path / "r2.json"
    rb.write_json(p1)
    rb.write_json(p2)

    d1 = json.loads(p1.read_text())
    d2 = json.loads(p2.read_text())
    # generated_at is produced from datetime.now() and may differ by microseconds.
    d1.pop("generated_at")
    d2.pop("generated_at")
    assert d1 == d2


def test_sanitize_string(t01_modules: Any) -> None:
    sanitize = t01_modules.sanitize.sanitize_string
    assert sanitize("token=secret123") == "token=<redacted>"
    assert sanitize("password: supersecret") == "password=<redacted>"
    assert (
        sanitize("Authorization: Bearer abc-def_123")
        == "Authorization: Bearer <redacted>"
    )
    assert sanitize("contact admin@example.com") == "contact <email-redacted>"
    assert (
        sanitize("http://localhost:8080/api") == "http://<local-endpoint-redacted>/api"
    )
    assert (
        sanitize("http://127.0.0.1:3000/health")
        == "http://<local-endpoint-redacted>/health"
    )


def test_sanitize_value_nested(t01_modules: Any) -> None:
    report = {
        "environment": {
            "token_line": "token=secret123",
            "nested": {"email": "admin@example.com"},
        },
        "checks": [
            {
                "details": {
                    "bearer": "Bearer tok",
                    "list": ["user@host.com"],
                }
            }
        ],
    }
    sanitized = t01_modules.sanitize.sanitize_for_evidence(report)

    assert sanitized["environment"]["token_line"] == "token=<redacted>"
    assert sanitized["environment"]["nested"]["email"] == "<email-redacted>"
    assert sanitized["checks"][0]["details"]["bearer"] == "Bearer <redacted>"
    assert sanitized["checks"][0]["details"]["list"] == ["<email-redacted>"]
    assert sanitized["secrets_included"] is False
