"""Round-trip validator: parse → edit → serialize → parse preserves canonical constructs."""

from __future__ import annotations

import re
from typing import Any

import yaml

from .base import ValidatorCheck


_FRONT_MATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", re.DOTALL)


class RoundTripValidator:
    """Validate Markdown/front-matter round-trip fidelity on synthetic fixtures."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    @staticmethod
    def _parse(text: str) -> tuple[dict[str, Any], str]:
        match = _FRONT_MATTER_RE.match(text)
        if not match:
            raise ValueError("front matter boundary not found")
        fm = yaml.safe_load(match.group(1))
        if not isinstance(fm, dict):
            raise ValueError("front matter is not a mapping")
        body = match.group(2)
        return fm, body

    @staticmethod
    def _serialize(front_matter: dict[str, Any], body: str) -> str:
        dumped = yaml.safe_dump(
            front_matter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=4096,
        )
        return f"---\n{dumped}---\n{body}"

    @staticmethod
    def _apply_edit(body: str, edit: dict[str, Any]) -> str:
        edit_type = edit.get("type", "replace")
        if edit_type == "replace":
            return body.replace(edit.get("old", ""), edit.get("new", ""), 1)
        if edit_type == "append":
            return body + edit.get("text", "")
        if edit_type == "prepend":
            return edit.get("text", "") + body
        raise ValueError(f"unknown edit type {edit_type}")

    @staticmethod
    def _deep_equal(a: Any, b: Any) -> bool:
        if isinstance(a, (bool, int)) and isinstance(b, (bool, int)):
            return a == b
        if type(a) is not type(b):
            return False
        if isinstance(a, dict):
            if a.keys() != b.keys():
                return False
            return all(RoundTripValidator._deep_equal(a[k], b[k]) for k in a)
        if isinstance(a, list):
            if len(a) != len(b):
                return False
            return all(RoundTripValidator._deep_equal(x, y) for x, y in zip(a, b))
        return a == b

    def validate(self) -> list[ValidatorCheck]:
        checks: list[ValidatorCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            expected_status = fixture.get("expected_status", "PASS")
            details: dict[str, Any] = {"fixture": name}

            try:
                original_fm, original_body = self._parse(fixture["markdown"])
            except Exception as exc:
                checks.append(
                    ValidatorCheck(
                        id=f"round_trip.{name}.parse",
                        status="FAIL",
                        expected="input fixture parses as Markdown+front matter",
                        actual=f"parse error: {exc}",
                        details=details,
                    )
                )
                continue

            try:
                intended_body = self._apply_edit(original_body, fixture.get("edit", {}))
                serialized = self._serialize(original_fm, intended_body)
                final_fm, final_body = self._parse(serialized)
            except Exception as exc:
                checks.append(
                    ValidatorCheck(
                        id=f"round_trip.{name}.round_trip",
                        status="FAIL",
                        expected="parse → edit → serialize → parse succeeds",
                        actual=f"round-trip error: {exc}",
                        details=details,
                    )
                )
                continue

            fm_ok = self._deep_equal(original_fm, final_fm)
            body_ok = final_body == intended_body
            preserved = fixture.get("expected_preserved", [])

            table_ok = True
            if "table" in preserved:
                original_rows = self._table_rows(original_body)
                final_rows = self._table_rows(final_body)
                table_ok = bool(original_rows) and original_rows == final_rows

            cyrillic_ok = True
            if "cyrillic" in preserved:
                cyrillic_ok = (
                    any(
                        "\u0400" <= ch <= "\u04ff"
                        for ch in original_body + str(original_fm)
                    )
                    and any(
                        "\u0400" <= ch <= "\u04ff" for ch in final_body + str(final_fm)
                    )
                )

            preserved_ok = all(
                (p == "table" and table_ok)
                or (p == "cyrillic" and cyrillic_ok)
                or self._field_preserved(original_fm, final_fm, p)
                for p in preserved
            )

            details.update(
                {
                    "front_matter_preserved": fm_ok,
                    "body_preserved": body_ok,
                    "expected_preserved": preserved,
                    "preserved_ok": preserved_ok,
                    "original_body_length": len(original_body),
                    "final_body_length": len(final_body),
                }
            )

            if expected_status == "PASS":
                if fm_ok and body_ok and preserved_ok:
                    checks.append(
                        ValidatorCheck(
                            id=f"round_trip.{name}.lossless",
                            status="PASS",
                            expected="canonical constructs preserved and only intended changes present",
                            actual="front matter, body and required constructs preserved through round-trip",
                            details=details,
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"round_trip.{name}.lossless",
                            status="FAIL",
                            expected="canonical constructs preserved and only intended changes present",
                            actual="round-trip lost or normalized content",
                            details=details,
                        )
                    )
            elif expected_status == "FAIL":
                expected_error = fixture.get("expected_error", "LOSS")
                if not (fm_ok and body_ok and preserved_ok):
                    checks.append(
                        ValidatorCheck(
                            id=f"round_trip.{name}.loss_detected",
                            status="PASS",
                            expected=f"construct loss detected ({expected_error})",
                            actual="round-trip introduced unintended changes",
                            details=details,
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"round_trip.{name}.loss_detected",
                            status="FAIL",
                            expected=f"construct loss detected ({expected_error})",
                            actual="round-trip unexpectedly preserved everything",
                            details=details,
                        )
                    )
            else:
                checks.append(
                    ValidatorCheck(
                        id=f"round_trip.{name}.unexpected_expected_status",
                        status="FAIL",
                        expected="expected status PASS or FAIL",
                        actual=f"unexpected expected status {expected_status}",
                        details=details,
                    )
                )

        return checks

    @staticmethod
    def _field_preserved(
        original: dict[str, Any], final: dict[str, Any], path: str
    ) -> bool:
        keys = path.split(".")
        a, b = original, final
        for k in keys:
            if not isinstance(a, dict) or k not in a:
                return False
            if not isinstance(b, dict) or k not in b:
                return False
            a, b = a[k], b[k]
        return RoundTripValidator._deep_equal(a, b)

    @staticmethod
    def _table_rows(body: str) -> list[list[str]]:
        """Extract Markdown table rows with cell content and alignment preserved."""
        rows: list[list[str]] = []
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                rows.append([cell.strip() for cell in stripped.split("|")[1:-1]])
        return rows
