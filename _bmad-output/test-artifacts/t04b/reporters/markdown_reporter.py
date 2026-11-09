"""Render a reviewable summary.md from a T04b report envelope."""

from __future__ import annotations

from typing import Any


def render_summary(report: dict[str, Any]) -> str:
    counts = report["counts"]
    total = sum(counts.values())
    lines: list[str] = [
        "# T04b Lossless TipTap Adapter and Browser Editor Gate Evidence Summary",
        "",
        f"- **Generated:** {report['generated_at']}",
        f"- **Contracts version:** {report['contracts_version']}",
        f"- **Baseline commit:** {report['baseline_commit']}",
        f"- **Spec baseline commit:** {report['spec_baseline_commit']}",
        f"- **Environment:** {report['environment']['sandbox']}",
        f"- **Sensitive data present:** {report['sensitive_data_included']}",
        "",
        "## Counts",
        "",
        f"- PASS: {counts.get('PASS', 0)}",
        f"- FAIL: {counts.get('FAIL', 0)}",
        f"- BLOCKED: {counts.get('BLOCKED', 0)}",
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
                f"- `{c['id']}` ({c['scenario_id']}): {c['actual']}; fixture `{c.get('fixture_path')}`"
            )
        lines.append("")

    if blocked:
        lines.append("### BLOCKED")
        for c in blocked[:20]:
            lines.append(f"- `{c['id']}` ({c['scenario_id']}): {c['actual']}")
        if len(blocked) > 20:
            lines.append(f"- ... and {len(blocked) - 20} more BLOCKED checks")
        lines.append("")

    if passed:
        lines.append("### PASS (sample)")
        for c in passed:
            lines.append(f"- `{c['id']}` ({c['scenario_id']}): {c['expected']}")
        lines.append("")

    lines.extend(
        [
            "## Rerun instructions",
            "",
            f"```bash\n{report['rerun_cmd']}\n```",
            "",
            "Real browser automation/IME/accessibility/XSS rendering checks remain BLOCKED until a sandboxed browser environment exists. "
            "This report contains only synthetic structural editor evidence; it does not claim production browser PASS.",
            "",
        ]
    )
    return "\n".join(lines)
