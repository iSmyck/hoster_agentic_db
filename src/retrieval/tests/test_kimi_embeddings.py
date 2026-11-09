"""Tests for the kimi.ai embeddings adapter."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from retrieval.app.adapters.embeddings import (
    EmbeddingAdapterError,
    StubEmbeddingAdapter,
    build_embedding_adapter,
)
from retrieval.app.adapters.kimi_embeddings import KimiEmbeddingAdapter


class _FakeTransport(httpx.HTTPTransport):
    """Mock httpx transport that returns a queued sequence of responses."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self._requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._requests.append(request)
        if not self._responses:
            raise RuntimeError("no more mock responses")
        return self._responses.pop(0)

    @property
    def requests(self) -> list[httpx.Request]:
        return self._requests


def _make_embeddings_response(texts: list[str], dimensions: int = 4) -> httpx.Response:
    """Build a kimi-style embeddings JSON response."""
    data = [
        {"object": "embedding", "embedding": [float(idx + 1)] * dimensions, "index": idx}
        for idx, _text in enumerate(texts)
    ]
    body = {
        "object": "list",
        "data": data,
        "model": "text-embedding-v2",
        "usage": {"prompt_tokens": 10, "total_tokens": 10},
    }
    return httpx.Response(200, json=body)


class TestKimiEmbeddingAdapter:
    def test_encode_batch_success(self) -> None:
        transport = _FakeTransport([_make_embeddings_response(["hello", "world"])])
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="secret-key",
            model="text-embedding-v2",
            client=httpx.Client(transport=transport),
        )

        result = adapter.encode(["hello", "world"])

        assert len(result) == 2
        assert len(result[0]) == 4
        assert result[0] == [1.0, 1.0, 1.0, 1.0]
        assert result[1] == [2.0, 2.0, 2.0, 2.0]

        assert len(transport.requests) == 1
        request = transport.requests[0]
        assert request.method == "POST"
        assert request.url.path == "/coding/v1/embeddings"
        assert request.headers["authorization"] == "Bearer secret-key"
        payload = json.loads(request.content)
        assert payload["model"] == "text-embedding-v2"
        assert payload["input"] == ["hello", "world"]

    def test_encode_empty_list_returns_empty(self) -> None:
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="secret-key",
            model="text-embedding-v2",
        )
        assert adapter.encode([]) == []

    def test_encode_4xx_raises_adapter_error(self) -> None:
        transport = _FakeTransport(
            [httpx.Response(401, json={"error": {"message": "Unauthorized"}})]
        )
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="secret-key",
            model="text-embedding-v2",
            client=httpx.Client(transport=transport),
        )

        with pytest.raises(EmbeddingAdapterError) as exc_info:
            adapter.encode(["hello"])

        assert "401" in str(exc_info.value)
        assert "secret-key" not in str(exc_info.value)

    def test_encode_5xx_raises_adapter_error(self) -> None:
        transport = _FakeTransport(
            [httpx.Response(503, json={"error": {"message": "Service Unavailable"}})]
        )
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="secret-key",
            model="text-embedding-v2",
            client=httpx.Client(transport=transport),
        )

        with pytest.raises(EmbeddingAdapterError) as exc_info:
            adapter.encode(["hello"])

        assert "503" in str(exc_info.value)
        assert "secret-key" not in str(exc_info.value)

    def test_encode_timeout_raises_adapter_error(self, monkeypatch: Any) -> None:
        class _TimeoutTransport(httpx.HTTPTransport):
            def handle_request(self, request: httpx.Request) -> httpx.Response:
                raise httpx.TimeoutException("request timed out")

        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="secret-key",
            model="text-embedding-v2",
            timeout=0.01,
            client=httpx.Client(transport=_TimeoutTransport()),
        )

        with pytest.raises(EmbeddingAdapterError) as exc_info:
            adapter.encode(["hello"])

        assert "timed out" in str(exc_info.value).lower()
        assert "secret-key" not in str(exc_info.value)

    def test_encode_malformed_json_raises_adapter_error(self) -> None:
        transport = _FakeTransport([httpx.Response(200, text="not-json")])
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="secret-key",
            model="text-embedding-v2",
            client=httpx.Client(transport=transport),
        )

        with pytest.raises(EmbeddingAdapterError) as exc_info:
            adapter.encode(["hello"])

        assert "JSON" in str(exc_info.value)
        assert "secret-key" not in str(exc_info.value)

    def test_encode_missing_data_raises_adapter_error(self) -> None:
        transport = _FakeTransport([httpx.Response(200, json={"object": "list"})])
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="secret-key",
            model="text-embedding-v2",
            client=httpx.Client(transport=transport),
        )

        with pytest.raises(EmbeddingAdapterError) as exc_info:
            adapter.encode(["hello"])

        assert "data" in str(exc_info.value).lower()
        assert "secret-key" not in str(exc_info.value)

    def test_encode_bad_embedding_item_raises_adapter_error(self) -> None:
        transport = _FakeTransport(
            [httpx.Response(200, json={"data": [{"embedding": "not-an-array"}]})]
        )
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="secret-key",
            model="text-embedding-v2",
            client=httpx.Client(transport=transport),
        )

        with pytest.raises(EmbeddingAdapterError) as exc_info:
            adapter.encode(["hello"])

        assert "embedding" in str(exc_info.value).lower()
        assert "secret-key" not in str(exc_info.value)

    def test_encode_wrong_count_raises_adapter_error(self) -> None:
        transport = _FakeTransport([_make_embeddings_response(["only-one"])])
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="secret-key",
            model="text-embedding-v2",
            client=httpx.Client(transport=transport),
        )

        with pytest.raises(EmbeddingAdapterError) as exc_info:
            adapter.encode(["hello", "world"])

        assert "2" in str(exc_info.value)
        assert "secret-key" not in str(exc_info.value)

    def test_error_messages_never_contain_api_key(self) -> None:
        transport = _FakeTransport(
            [httpx.Response(500, text="Internal Server Error: secret-key leaked")]
        )
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="super-secret-api-key-12345",
            model="text-embedding-v2",
            client=httpx.Client(transport=transport),
        )

        with pytest.raises(EmbeddingAdapterError) as exc_info:
            adapter.encode(["hello"])

        assert "super-secret-api-key-12345" not in str(exc_info.value)
        assert "super-secret-api-key-12345" not in repr(exc_info.value)

    def test_api_key_not_in_repr(self) -> None:
        adapter = KimiEmbeddingAdapter(
            api_base_url="https://api.kimi.com/coding/v1",
            api_key="super-secret",
            model="text-embedding-v2",
        )
        assert "super-secret" not in repr(adapter)


class TestBuildEmbeddingAdapter:
    def test_build_returns_kimi_adapter(self) -> None:
        class _Settings:
            EMBEDDING_MODEL = "kimi"
            EMBEDDING_DIMENSIONS = 1024
            KIMI_API_BASE_URL = "https://api.kimi.com/coding/v1"
            KIMI_API_KEY = "secret"
            KIMI_EMBEDDING_MODEL = "text-embedding-v2"

        adapter = build_embedding_adapter(_Settings())
        assert isinstance(adapter, KimiEmbeddingAdapter)

    def test_build_returns_stub_adapter(self) -> None:
        class _Settings:
            EMBEDDING_MODEL = "stub-deterministic"
            EMBEDDING_DIMENSIONS = 128

        adapter = build_embedding_adapter(_Settings())
        assert isinstance(adapter, StubEmbeddingAdapter)
