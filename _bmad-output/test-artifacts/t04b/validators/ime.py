"""IME validator: Russian composition ordering preserved."""

from __future__ import annotations

from typing import Any

from .base import ValidatorCheck


class IMEValidator:
    """Validate synthetic IME composition sequences."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[ValidatorCheck]:
        checks: list[ValidatorCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            expected_status = fixture.get("expected_status", "PASS")
            sequence = fixture.get("sequence", [])
            expected_text = fixture.get("expected_text", "")
            expected_sequence = fixture.get("expected_sequence", sequence)
            composed = "".join(sequence)
            order_preserved = list(sequence) == list(expected_sequence)
            text_preserved = composed == expected_text
            details: dict[str, Any] = {
                "sequence_length": len(sequence),
                "composed_length": len(composed),
                "order_preserved": order_preserved,
                "text_preserved": text_preserved,
            }

            if expected_status == "PASS":
                if order_preserved and text_preserved:
                    checks.append(
                        ValidatorCheck(
                            id=f"ime.{name}.ordering",
                            status="PASS",
                            expected="Russian IME composition order and final text preserved",
                            actual=f"order preserved; composed text matches ({composed!r})",
                            details=details,
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"ime.{name}.ordering",
                            status="FAIL",
                            expected="Russian IME composition order and final text preserved",
                            actual="IME reordering or text mismatch detected",
                            details=details,
                        )
                    )
            elif expected_status == "FAIL":
                if not (order_preserved and text_preserved):
                    checks.append(
                        ValidatorCheck(
                            id=f"ime.{name}.reorder_detected",
                            status="PASS",
                            expected="IME reordering detected as failure",
                            actual="composition order or final text differs from expected",
                            details=details,
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"ime.{name}.reorder_detected",
                            status="FAIL",
                            expected="IME reordering detected as failure",
                            actual="order and text unexpectedly preserved",
                            details=details,
                        )
                    )
            else:
                checks.append(
                    ValidatorCheck(
                        id=f"ime.{name}.unexpected_expected_status",
                        status="FAIL",
                        expected="expected status PASS or FAIL",
                        actual=f"unexpected expected status {expected_status}",
                        details=details,
                    )
                )

        return checks
