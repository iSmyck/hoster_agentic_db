"""Kroki validation port for Mermaid (KBI.5.3)."""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

_PREFIXES = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
)


class KrokiError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class KrokiClient(ABC):
    available: bool

    @abstractmethod
    def validate_mermaid(self, source: str) -> bool:
        """Return True when Kroki can render the source."""


class StubKrokiClient(KrokiClient):
    def __init__(self, *, available: bool = False) -> None:
        self.available = available
        self.fail_next: bool = False
        self.calls: list[str] = []

    def validate_mermaid(self, source: str) -> bool:
        self.calls.append(source)
        if self.fail_next:
            self.fail_next = False
            return False
        stripped = source.strip()
        if "INVALID" in stripped:
            return False
        return any(stripped.startswith(prefix) for prefix in _PREFIXES)


class HttpKrokiClient(KrokiClient):
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(base_url=self.base_url)
        self.available = bool(self.base_url)

    def validate_mermaid(self, source: str) -> bool:
        if not self.available:
            raise KrokiError("Kroki is not configured")
        url = f"{self.base_url}/mermaid/svg"
        try:
            response = self._client.post(url, content=source.encode("utf-8"), timeout=15)
        except httpx.HTTPError as exc:
            raise KrokiError(f"Kroki request failed: {exc}") from exc
        return response.status_code < 400
