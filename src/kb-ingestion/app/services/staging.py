"""Validation and staging for raw convert uploads."""

from __future__ import annotations

import re
import uuid

from ..adapters.object_store import ObjectStore, StagedObject

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z0-9_/-]+$")
_ALLOWED_PROFILES = frozenset({"strict", "pii_permitted"})


class StagingError(Exception):
    """Client or policy error before or during staging."""

    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class StagingService:
    """Accepts validated uploads and stages them in object storage."""

    def __init__(self, store: ObjectStore, max_upload_size_bytes: int) -> None:
        self._store = store
        self._max_upload_size_bytes = max_upload_size_bytes

    def validate_metadata(
        self,
        *,
        space_id: str,
        client_id: str,
        data_profile: str,
        legal_basis: str | None,
    ) -> None:
        """Reject invalid form metadata before reading the upload body."""
        self._validate_identifier(space_id, "INVALID_SPACE_ID", "invalid space_id")
        self._validate_identifier(client_id, "INVALID_CLIENT_ID", "invalid client_id")
        self._validate_profile(data_profile, legal_basis)

    def stage_convert_upload(
        self,
        *,
        space_id: str,
        client_id: str,
        data_profile: str,
        legal_basis: str | None,
        content: bytes,
        media_type: str | None,
    ) -> StagedObject:
        self.validate_metadata(
            space_id=space_id,
            client_id=client_id,
            data_profile=data_profile,
            legal_basis=legal_basis,
        )
        self._validate_size(content)
        resolved_media = media_type or "application/octet-stream"
        object_id = uuid.uuid4().hex
        return self._store.put(
            space_id,
            client_id,
            object_id,
            content,
            resolved_media,
        )

    def _validate_identifier(self, value: str, code: str, message: str) -> None:
        if not value or not _IDENTIFIER_RE.fullmatch(value):
            raise StagingError(code, message)

    def _validate_profile(self, data_profile: str, legal_basis: str | None) -> None:
        if data_profile not in _ALLOWED_PROFILES:
            raise StagingError("INVALID_DATA_PROFILE", "invalid data_profile")
        if data_profile == "pii_permitted" and not (legal_basis and legal_basis.strip()):
            raise StagingError("LEGAL_BASIS_REQUIRED", "legal_basis is required for pii_permitted")

    def _validate_size(self, content: bytes) -> None:
        if len(content) > self._max_upload_size_bytes:
            raise StagingError(
                "SIZE_LIMIT_EXCEEDED",
                f"upload exceeds {self._max_upload_size_bytes} bytes",
                http_status=413,
            )