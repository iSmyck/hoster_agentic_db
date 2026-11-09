"""Embedding provider port, stub implementation, and production placeholder."""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from typing import Any


class EmbeddingAdapterError(Exception):
    """Raised when embedding generation fails."""


class EmbeddingAdapter(ABC):
    """Outbound port for text-to-vector inference."""

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return one normalized embedding vector for each input text."""


class StubEmbeddingAdapter(EmbeddingAdapter):
    """Deterministic embedding stub.

    Produces a unit-length vector derived from the SHA-256 of the input text.
    The stub is used for tests and local development; real model inference is
    intentionally blocked in the MVP.
    """

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(text) for text in texts]

    def _vector_for(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Generate ``dimensions`` deterministic floats from the digest.
        floats: list[float] = []
        for i in range(self.dimensions):
            byte_a = digest[(i * 2) % len(digest)]
            byte_b = digest[(i * 2 + 1) % len(digest)]
            value = (byte_a + byte_b / 256.0) / 256.0
            floats.append(value)
        return _unit_normalize(floats)


def _unit_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (norm_a * norm_b)


class ProductionEmbeddingAdapter(EmbeddingAdapter):
    """Placeholder for a managed production embedding model.

    Real model inference requires an approved inference inventory and is left
    as a future integration point.
    """

    def __init__(self, model: str, dimensions: int) -> None:
        self.model = model
        self.dimensions = dimensions

    def encode(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingAdapterError(
            "production embedding model is not configured; "
            "use StubEmbeddingAdapter for tests"
        )


def build_embedding_adapter(settings: Any) -> EmbeddingAdapter:
    """Factory returning the configured embedding adapter."""
    if settings.EMBEDDING_MODEL == "stub-deterministic":
        return StubEmbeddingAdapter(settings.EMBEDDING_DIMENSIONS)
    return ProductionEmbeddingAdapter(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIMENSIONS)
