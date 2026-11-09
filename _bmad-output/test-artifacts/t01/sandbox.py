"""Synthetic repository-per-Space provisioning stub."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fixtures.spaces import sales_pricing_space, sales_space


class GitLabSandbox:
    """Stub provisioner for two disposable repository-per-Space fixtures.

    Real GitLab/IdP/CI/hoster.ai sandboxes are unavailable in the T01 synthetic
    harness; this module records the intended provisioning state and returns
    BLOCKED when API calls would require a live endpoint.
    """

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = base_url
        self.token = token
        self.available = False
        self.spaces: dict[str, dict[str, Any]] = {
            "sales": sales_space(),
            "sales-pricing": sales_pricing_space(),
        }

    def provision(self) -> dict[str, Any]:
        """Return the in-memory fixture description; no live API calls."""
        return {
            "status": "BLOCKED",
            "reason": "real GitLab sandbox not provisioned for T01",
            "spaces": self.spaces,
        }

    def create_repository(self, space_id: str) -> dict[str, Any]:
        return {
            "status": "BLOCKED",
            "reason": "real GitLab API unavailable",
            "space_id": space_id,
        }


def load_or_stub(path: Path) -> Any:
    """Load a fixture file if it exists, otherwise return None."""
    if path.exists():
        import json

        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None
