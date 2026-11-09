"""Kimi.ai embeddings adapter."""

from __future__ import annotations

from typing import Any

import httpx

from retrieval.app.adapters.embeddings import EmbeddingAdapter, EmbeddingAdapterError


class KimiEmbeddingAdapter(EmbeddingAdapter):
    """Production embedding adapter calling the kimi.ai embeddings endpoint."""

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model: str,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = client

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"api_base_url={self.api_base_url!r}, "
            f"api_key=***, "
            f"model={self.model!r}, "
            f"timeout={self.timeout})"
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""
        if not texts:
            return []

        url = f"{self.api_base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "input": list(texts)}

        client = self._client
        if client is None:
            with httpx.Client() as client:
                response = self._post(client, url, headers, payload)
        else:
            response = self._post(client, url, headers, payload)

        try:
            data = response.json()
        except Exception as exc:
            raise EmbeddingAdapterError("kimi embeddings response was not valid JSON") from exc

        embeddings = self._extract_embeddings(data, len(texts))
        if len(embeddings) != len(texts):
            raise EmbeddingAdapterError(
                f"kimi embeddings returned {len(embeddings)} vectors for {len(texts)} texts"
            )
        return embeddings

    def _post(
        self,
        client: httpx.Client,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> httpx.Response:
        """Execute the HTTP POST and map httpx errors to EmbeddingAdapterError."""
        try:
            response = client.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise EmbeddingAdapterError(
                f"kimi embeddings request timed out after {self.timeout}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise EmbeddingAdapterError(
                f"kimi embeddings request failed: HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise EmbeddingAdapterError(f"kimi embeddings request failed: {exc}") from exc
        return response

    def _extract_embeddings(self, data: Any, expected_count: int) -> list[list[float]]:
        """Extract embedding vectors from a kimi-style JSON response."""
        if not isinstance(data, dict):
            raise EmbeddingAdapterError("kimi embeddings response body was not a JSON object")

        items = data.get("data")
        if not isinstance(items, list):
            raise EmbeddingAdapterError("kimi embeddings response missing 'data' list")

        embeddings: list[list[float]] = []
        for item in items:
            if not isinstance(item, dict):
                raise EmbeddingAdapterError("kimi embeddings response item was not an object")
            embedding = item.get("embedding")
            if not isinstance(embedding, list) or not all(
                isinstance(v, (int, float)) for v in embedding
            ):
                raise EmbeddingAdapterError(
                    "kimi embeddings response item missing valid 'embedding' array"
                )
            embeddings.append([float(v) for v in embedding])

        return embeddings
