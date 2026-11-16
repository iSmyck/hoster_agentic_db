"""Shared hashing and object-key helpers for staging adapters."""

from __future__ import annotations

import hashlib
from urllib.parse import quote


def sha256_hex(data: bytes) -> str:
    """Return the hex SHA-256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def object_key(space_id: str, client_id: str, object_id: str) -> str:
    """Build a collision-safe object key from identity parts.

    Raw ``/`` joins collide when ``space_id`` or ``client_id`` contain slashes
    (allowed by the ingest id charset). Percent-encoding each part keeps
    ``(a/b, c)`` distinct from ``(a, b/c)``.
    """
    return f"{quote(space_id, safe='')}/{quote(client_id, safe='')}/{quote(object_id, safe='')}"
