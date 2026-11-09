"""Keycloak OIDC identity adapter.

Provides token introspection and userinfo resolution against a Keycloak realm
without leaking client secrets or access tokens in logs or error messages.
"""

from __future__ import annotations

from typing import Any

import httpx


class IdentityAdapterError(Exception):
    """Raised when an upstream identity adapter fails to resolve a token."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class KeycloakIdentityAdapter:
    """Resolve bearer tokens to normalized external identity refs via Keycloak."""

    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        timeout: float = 10.0,
    ) -> None:
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._issuer = f"{self.keycloak_url}/realms/{self.realm}"

    def _introspection_url(self) -> str:
        return (
            f"{self.keycloak_url}/realms/{self.realm}"
            "/protocol/openid-connect/token/introspect"
        )

    def _userinfo_url(self) -> str:
        return (
            f"{self.keycloak_url}/realms/{self.realm}"
            "/protocol/openid-connect/userinfo"
        )

    def introspect_token(self, access_token: str) -> dict[str, Any]:
        """Introspect an access token and return the Keycloak response."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self._introspection_url(),
                    data={
                        "token": access_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "token_type_hint": "access_token",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise IdentityAdapterError(
                "INTROSPECTION_TIMEOUT",
                "Keycloak token introspection timed out",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise IdentityAdapterError(
                "INTROSPECTION_HTTP_ERROR",
                f"Keycloak introspection returned HTTP {exc.response.status_code}",
            ) from exc
        except httpx.RequestError as exc:
            raise IdentityAdapterError(
                "INTROSPECTION_REQUEST_ERROR",
                "Unable to reach Keycloak introspection endpoint",
            ) from exc

        return response.json()

    def userinfo(self, access_token: str) -> dict[str, Any]:
        """Call the Keycloak userinfo endpoint for a valid access token."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    self._userinfo_url(),
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise IdentityAdapterError(
                "USERINFO_TIMEOUT",
                "Keycloak userinfo request timed out",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise IdentityAdapterError(
                "USERINFO_HTTP_ERROR",
                f"Keycloak userinfo returned HTTP {exc.response.status_code}",
            ) from exc
        except httpx.RequestError as exc:
            raise IdentityAdapterError(
                "USERINFO_REQUEST_ERROR",
                "Unable to reach Keycloak userinfo endpoint",
            ) from exc

        return response.json()

    def resolve_external_refs(self, access_token: str) -> dict[str, Any]:
        """Return a normalized external_ref dict from a bearer token.

        The result always contains ``issuer`` and ``sub`` and includes any
        additional claims returned by Keycloak introspection (e.g. ``email``,
        ``preferred_username``) without exposing secrets or the raw token.

        Introspection is used as the single source of truth because some
        Keycloak clients cannot call ``/userinfo`` for tokens issued via the
        direct-access grant unless the realm explicitly maps the userinfo
        audience.
        """
        introspection = self.introspect_token(access_token)
        if not introspection.get("active"):
            raise IdentityAdapterError("TOKEN_INVALID", "Access token is not active")

        sub = introspection.get("sub")
        if not sub:
            raise IdentityAdapterError(
                "TOKEN_MISSING_SUB",
                "Introspection response did not contain a subject",
            )

        external_ref: dict[str, Any] = {
            "issuer": self._issuer,
            "sub": sub,
        }
        for key in ("email", "preferred_username", "name", "given_name", "family_name"):
            value = introspection.get(key)
            if value:
                external_ref[key] = value

        return external_ref
