"""Render a reviewable summary.md from a report envelope."""

from __future__ import annotations

from typing import Any


def render_summary(report: dict[str, Any]) -> str:
    counts = report["counts"]
    total = sum(counts.values())
    lines: list[str] = [
        "# T01 Contract Test Evidence Summary",
        "",
        f"- **Generated:** {report['generated_at']}",
        f"- **Contracts version:** {report['contracts_version']}",
        f"- **Baseline commit:** {report['baseline_commit']}",
        f"- **Environment:** {report['environment']['sandbox']}",
        f"- **Sensitive data present:** {report['secrets_included']}",
        "",
        "## Counts",
        "",
        f"- PASS: {counts.get('PASS', 0)}",
        f"- FAIL: {counts.get('FAIL', 0)}",
        f"- BLOCKED: {counts.get('BLOCKED', 0)}",
        f"- NOT_EXECUTED: {counts.get('NOT_EXECUTED', 0)}",
        f"- **Total:** {total}",
        "",
        "## Top findings",
        "",
    ]

    blocked = [c for c in report["checks"] if c["status"] == "BLOCKED"]
    failed = [c for c in report["checks"] if c["status"] == "FAIL"]
    passed = [c for c in report["checks"] if c["status"] == "PASS"][:10]

    if failed:
        lines.append("### FAIL")
        for c in failed:
            lines.append(
                f"- `{c['id']}` ({c['cf_id']}): {c['actual']}; fixture `{c.get('fixture_path')}`"
            )
        lines.append("")

    if blocked:
        lines.append("### BLOCKED / DESIGN_NOT_EXECUTED")
        for c in blocked[:20]:
            lines.append(f"- `{c['id']}` ({c['cf_id']}): {c['actual']}")
        if len(blocked) > 20:
            lines.append(f"- ... and {len(blocked) - 20} more BLOCKED checks")
        lines.append("")

    if passed:
        lines.append("### PASS (sample)")
        for c in passed:
            lines.append(f"- `{c['id']}` ({c['cf_id']}): {c['expected']}")
        lines.append("")

    lines.extend(
        [
            "## Rerun instructions",
            "",
            f"```bash\n{report['rerun_cmd']}\n```",
            "",
            "Real GitLab/IdP/CI/hoster.ai integration checks remain BLOCKED until their sandboxes and credentials exist. "
            "This report contains only synthetic structural/contract evidence; it does not claim production integration PASS.",
            "",
        ]
    )
    return "\n".join(lines)
