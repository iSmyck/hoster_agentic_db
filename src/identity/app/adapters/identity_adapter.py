"""Stub interface for upstream LDAP/OIDC identity adapters.

Real LDAP/OIDC integration is intentionally deferred; this module defines the
seam so services remain hexagonal and future IdP clients can plug in without
touching API or service code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IdentityAdapter(ABC):
    """Abstract upstream identity provider adapter."""

    @abstractmethod
    def authenticate(self, credentials: dict[str, Any]) -> dict[str, Any]:
        """Return normalized identity attributes on successful upstream auth.

        Expected return shape::

            {
                "stable_id": "...",
                "username": "...",
                "display_name": "...",
                "groups": ["group-a", "group-b"],
                "issuer": "ldap|oidc",
            }
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_groups(self, stable_id: str) -> list[str]:
        """Return resolved nested group membership for a stable identity."""
        raise NotImplementedError


class StubIdentityAdapter(IdentityAdapter):
    """No-op adapter for MVP development and offline tests."""

    def authenticate(self, credentials: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("stub adapter does not authenticate")

    def fetch_groups(self, stable_id: str) -> list[str]:
        raise NotImplementedError("stub adapter does not fetch groups")
