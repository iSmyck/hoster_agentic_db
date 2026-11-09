#!/usr/bin/env python3
"""Manual smoke test for the kimi.ai embeddings adapter.

Loads configuration from the project's .env file and calls the live kimi.ai
embeddings endpoint for two short texts. Prints only vector dimensions and a
few sample values; the API key is never logged.

Run from the project root so the .env file is resolved:
    uv run python src/retrieval/scripts/smoke_kimi_embeddings.py
"""

from __future__ import annotations

from retrieval.app.adapters.kimi_embeddings import KimiEmbeddingAdapter
from retrieval.app.core.config import Settings


def main() -> None:
    settings = Settings()
    adapter = KimiEmbeddingAdapter(
        api_base_url=settings.KIMI_API_BASE_URL,
        api_key=settings.KIMI_API_KEY,
        model=settings.KIMI_EMBEDDING_MODEL,
    )

    vectors = adapter.encode(["hello", "world"])
    print(f"encoded {len(vectors)} text(s)")
    for idx, vector in enumerate(vectors):
        print(f"  vector[{idx}] dimension={len(vector)} sample={vector[:5]}")


if __name__ == "__main__":
    main()
