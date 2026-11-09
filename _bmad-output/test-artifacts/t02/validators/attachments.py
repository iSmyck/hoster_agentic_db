"""Attachment tuple validator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .document_store import Document, Space


REQUIRED_FIELDS = (
    "object_id",
    "version",
    "sha256",
    "size",
    "media_type",
    "source_ref",
)


@dataclass
class AttachmentCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


class AttachmentValidator:
    """Validate every attachment exposes the full immutable tuple."""

    def __init__(self, spaces: dict[str, Space]) -> None:
        self.spaces = spaces

    def validate(self) -> list[AttachmentCheck]:
        checks: list[AttachmentCheck] = []
        for space in self.spaces.values():
            for doc in space.documents:
                for idx, attachment in enumerate(doc.attachments):
                    check_id = f"attachments.{space.space_id}.{doc.path}.{idx}"
                    if not isinstance(attachment, dict):
                        checks.append(
                            AttachmentCheck(
                                id=check_id,
                                status="FAIL",
                                expected="attachment is an object",
                                actual=f"got {type(attachment).__name__}",
                                details={"path": doc.path, "index": idx},
                            )
                        )
                        continue
                    missing = [f for f in REQUIRED_FIELDS if f not in attachment]
                    if missing:
                        checks.append(
                            AttachmentCheck(
                                id=check_id,
                                status="FAIL",
                                expected=f"attachment has required fields {REQUIRED_FIELDS}",
                                actual=f"missing {missing}",
                                details={
                                    "path": doc.path,
                                    "index": idx,
                                    "attachment": attachment,
                                    "missing": missing,
                                },
                            )
                        )
                    else:
                        checks.append(
                            AttachmentCheck(
                                id=check_id,
                                status="PASS",
                                expected="attachment exposes full immutable tuple",
                                actual=f"object_id={attachment['object_id']}, version={attachment['version']}",
                                details={
                                    "path": doc.path,
                                    "index": idx,
                                    "object_id": attachment["object_id"],
                                    "version": attachment["version"],
                                    "sha256": attachment["sha256"],
                                    "size": attachment["size"],
                                    "media_type": attachment["media_type"],
                                    "source_ref": attachment["source_ref"],
                                    "media_class": attachment["media_class"],
                                    "verification_status": attachment[
                                        "verification_status"
                                    ],
                                },
                            )
                        )
        return checks
