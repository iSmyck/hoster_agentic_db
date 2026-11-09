"""Identity stable-key validator for synthetic OIDC/AD/LDAP fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IdentityCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


def _identity_key(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (key_type, stable_key) if the payload carries a valid identity key."""
    source = payload.get("source", "oidc")
    if source == "oidc":
        issuer = payload.get("issuer")
        sub = payload.get("sub")
        if issuer and sub:
            return ("issuer+sub", f"{issuer}:{sub}")
        return (None, None)
    if source in ("ad", "ldap"):
        directory = payload.get("directory")
        if source == "ad":
            guid = payload.get("object_guid") or payload.get("objectGUID")
            if directory and guid:
                return ("directory+objectGUID", f"{directory}:{guid}")
        else:
            uuid = payload.get("entry_uuid") or payload.get("entryUUID")
            if directory and uuid:
                return ("directory+entryUUID", f"{directory}:{uuid}")
        return (None, None)
    return (None, None)


class IdentityValidator:
    """Validate that identity payloads use issuer-scoped sub, objectGUID or entryUUID."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[IdentityCheck]:
        checks: list[IdentityCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            payload = fixture.get("payload", {})
            expected_valid = bool(fixture.get("expected_valid", True))
            key_type, stable_key = _identity_key(payload)

            errors: list[str] = []
            source = payload.get("source", "oidc")

            if source == "oidc":
                if not payload.get("issuer"):
                    errors.append("missing issuer")
                if not payload.get("sub"):
                    errors.append("missing sub")
            elif source == "ad":
                if not payload.get("directory"):
                    errors.append("missing directory")
                if not (payload.get("object_guid") or payload.get("objectGUID")):
                    errors.append("missing objectGUID")
            elif source == "ldap":
                if not payload.get("directory"):
                    errors.append("missing directory")
                if not (payload.get("entry_uuid") or payload.get("entryUUID")):
                    errors.append("missing entryUUID")
            else:
                errors.append(f"unknown source {source}")

            # Email/login must be present but are explicitly not the identity key.
            if not payload.get("email") and not payload.get("login"):
                errors.append("no contact attribute (email/login)")

            is_valid = not errors and stable_key is not None

            if expected_valid and is_valid:
                checks.append(
                    IdentityCheck(
                        id=f"identity.stable_id.{name}",
                        status="PASS",
                        expected=f"{source} identity has stable key",
                        actual=f"stable key {key_type}={stable_key}",
                        details={
                            "source": source,
                            "key_type": key_type,
                            "stable_key": stable_key,
                            "email": payload.get("email"),
                            "login": payload.get("login"),
                        },
                    )
                )
            elif expected_valid and not is_valid:
                checks.append(
                    IdentityCheck(
                        id=f"identity.stable_id.{name}",
                        status="FAIL",
                        expected=f"{source} identity has stable key",
                        actual=f"missing stable key: {errors}",
                        details={
                            "source": source,
                            "errors": errors,
                            "payload": payload,
                        },
                    )
                )
            elif not expected_valid and is_valid:
                checks.append(
                    IdentityCheck(
                        id=f"identity.stable_id.{name}",
                        status="FAIL",
                        expected="identity missing stable key or using email/login as key",
                        actual=f"unexpectedly valid with key {key_type}={stable_key}",
                        details={
                            "source": source,
                            "key_type": key_type,
                            "stable_key": stable_key,
                        },
                    )
                )
            else:
                checks.append(
                    IdentityCheck(
                        id=f"identity.stable_id.{name}",
                        status="PASS",
                        expected="identity missing stable key or using email/login as key",
                        actual=f"correctly rejected: {errors}",
                        details={
                            "source": source,
                            "errors": errors,
                            "payload": payload,
                        },
                    )
                )
        return checks
