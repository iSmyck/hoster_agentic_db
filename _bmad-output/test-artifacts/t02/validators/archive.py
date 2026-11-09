"""Archive invariant validator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .document_store import Document, Space


@dataclass
class ArchiveCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


class ArchiveValidator:
    """Validate archive bidirectional invariant: archived iff archive present."""

    def __init__(self, spaces: dict[str, Space]) -> None:
        self.spaces = spaces

    def validate(self) -> list[ArchiveCheck]:
        checks: list[ArchiveCheck] = []
        for space in self.spaces.values():
            for doc in space.documents:
                check_id = f"archive.{space.space_id}.{doc.path}.invariant"
                archived = doc.archived
                has_archive = doc.archive is not None
                if archived == has_archive:
                    checks.append(
                        ArchiveCheck(
                            id=check_id,
                            status="PASS",
                            expected="archived flag and archive block are consistent",
                            actual=f"archived={archived}, has_archive={has_archive}",
                            details={
                                "path": doc.path,
                                "document_id": doc.document_id,
                                "archived": archived,
                                "has_archive": has_archive,
                            },
                        )
                    )
                else:
                    checks.append(
                        ArchiveCheck(
                            id=check_id,
                            status="FAIL",
                            expected="archived=true iff archive block is present",
                            actual=f"archived={archived}, has_archive={has_archive}",
                            details={
                                "path": doc.path,
                                "document_id": doc.document_id,
                                "archived": archived,
                                "has_archive": has_archive,
                            },
                        )
                    )

                # If archive is present, validate required sub-fields.
                if doc.archive is not None:
                    sub_check_id = f"archive.{space.space_id}.{doc.path}.fields"
                    required = ("archived_at", "reason", "replacement_document_id")
                    missing = [f for f in required if f not in doc.archive]
                    if missing:
                        checks.append(
                            ArchiveCheck(
                                id=sub_check_id,
                                status="FAIL",
                                expected=f"archive block has required fields {required}",
                                actual=f"missing {missing}",
                                details={
                                    "path": doc.path,
                                    "archive": doc.archive,
                                    "missing": missing,
                                },
                            )
                        )
                    else:
                        checks.append(
                            ArchiveCheck(
                                id=sub_check_id,
                                status="PASS",
                                expected="archive block has required fields",
                                actual=f"archive fields present: {required}",
                                details={
                                    "path": doc.path,
                                    "archived_at": doc.archive["archived_at"],
                                    "replacement_document_id": doc.archive[
                                        "replacement_document_id"
                                    ],
                                },
                            )
                        )
        return checks
