"""Unit tests for T04b front-matter boundary and XSS gate validators."""

from __future__ import annotations

from typing import Any


def test_front_matter_boundary_pass(t04b_modules: Any) -> None:
    fixture = {
        "name": "valid",
        "markdown": "---\ntitle: Hello\n---\nBody here\n",
        "expected_status": "PASS",
    }
    checks = t04b_modules.front_matter_boundary.FrontMatterBoundaryValidator(
        [fixture]
    ).validate()

    assert len(checks) == 1
    assert checks[0].status == "PASS"


def test_front_matter_boundary_fail(t04b_modules: Any) -> None:
    fixture = {
        "name": "invalid",
        "markdown": "title: Hello\n---\nBody here\n",
        "expected_status": "FAIL",
    }
    checks = t04b_modules.front_matter_boundary.FrontMatterBoundaryValidator(
        [fixture]
    ).validate()

    assert len(checks) == 1
    assert checks[0].status == "PASS"


def test_xss_rejects_script(t04b_modules: Any) -> None:
    fixture = {
        "name": "script",
        "payloads": [
            {
                "value": "<script>alert(1)</script>",
                "expected": "reject",
                "label": "script_tag",
            },
            {
                "value": "<img src=x onerror=alert(1)>",
                "expected": "reject",
                "label": "event_handler",
            },
            {
                "value": "javascript:void(0)",
                "expected": "reject",
                "label": "js_protocol",
            },
        ],
    }
    checks = t04b_modules.xss.XSSValidator([fixture]).validate()

    assert len(checks) == 3
    assert all(c.status == "PASS" for c in checks)


def test_xss_allows_safe_markdown(t04b_modules: Any) -> None:
    fixture = {
        "name": "safe",
        "payloads": [
            {
                "value": "# Hello\n\nworld",
                "expected": "allow",
                "label": "heading",
            },
            {
                "value": "[link](http://example.com)",
                "expected": "allow",
                "label": "link",
            },
        ],
    }
    checks = t04b_modules.xss.XSSValidator([fixture]).validate()

    assert len(checks) == 2
    assert all(c.status == "PASS" for c in checks)


def test_xss_mdx_rejected(t04b_modules: Any) -> None:
    fixture = {
        "name": "mdx",
        "payloads": [
            {
                "value": "<Component prop={value} />",
                "expected": "reject",
                "label": "jsx_component",
            }
        ],
    }
    checks = t04b_modules.xss.XSSValidator([fixture]).validate()

    assert len(checks) == 1
    assert checks[0].status == "PASS"
