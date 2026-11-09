"""End-to-end MVP tests for the Retrieval + Indexing adapter."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from retrieval.app.adapters.embeddings import (
    EmbeddingAdapter,
    EmbeddingAdapterError,
    ProductionEmbeddingAdapter,
    StubEmbeddingAdapter,
    build_embedding_adapter,
    cosine_similarity,
)
from retrieval.app.adapters.go_client import StubGOClient
from retrieval.app.adapters.identity_client import IdentityClientError, StubIdentityClient
from retrieval.app.services.indexing import activate_pointer, build_index
from retrieval.app.services.retrieval_error import RetrievalServiceError


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestIndexBuild:
    def test_build_index_creates_generation(
        self,
        client: TestClient,
        go_client: StubGOClient,
        space_id: str,
        snapshot_sha: str,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/page.md", "type": "blob", "sha": "b" * 40},
        ]
        go_client.state[("doc", space_id, "docs/page.md", snapshot_sha)] = (
            "This is a sample document about retrieval systems."
        )

        resp = client.post(
            "/api/kb/v1/index/build",
            json={"space_id": space_id, "snapshot_sha": snapshot_sha},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["space_id"] == space_id
        assert body["snapshot_sha"] == snapshot_sha
        assert body["status"] == "ready"
        assert body["chunks_indexed"] > 0

    def test_build_index_requires_forty_char_sha(
        self,
        client: TestClient,
        space_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/index/build",
            json={"space_id": space_id, "snapshot_sha": "short"},
        )
        assert resp.status_code == 422


class TestIndexActivate:
    def test_activate_pointer(
        self,
        client: TestClient,
        go_client: StubGOClient,
        identity_client: StubIdentityClient,
        space_id: str,
        snapshot_sha: str,
        actor_id: uuid.UUID,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/page.md", "type": "blob", "sha": "b" * 40},
        ]
        go_client.state[("doc", space_id, "docs/page.md", snapshot_sha)] = (
            "Retrieval systems return relevant documents."
        )

        build_resp = client.post(
            "/api/kb/v1/index/build",
            json={"space_id": space_id, "snapshot_sha": snapshot_sha},
        )
        generation_id = build_resp.json()["generation_id"]

        resp = client.post(
            "/api/kb/v1/index/activate",
            json={
                "space_id": space_id,
                "profile": "default",
                "generation_id": str(generation_id),
                "fence_token": 0,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["space_id"] == space_id
        assert body["profile"] == "default"
        assert body["generation_id"] == generation_id
        assert body["fence_token"] == 1
        assert body["active"] is True

        # Search should now succeed.
        search_resp = client.post(
            "/api/kb/v1/search",
            json={
                "space_id": space_id,
                "query": "retrieval documents",
                "actor_id": str(actor_id),
                "profile": "default",
                "mode": "hybrid",
            },
        )
        assert search_resp.status_code == 200, search_resp.text
        search_body = search_resp.json()
        assert search_body["space_id"] == space_id
        assert search_body["profile"] == "default"
        assert search_body["snapshot_sha"] == snapshot_sha
        assert len(search_body["results"]) > 0

    def test_activate_with_wrong_fence_token_conflicts(
        self,
        client: TestClient,
        go_client: StubGOClient,
        space_id: str,
        snapshot_sha: str,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/page.md", "type": "blob", "sha": "b" * 40},
        ]
        go_client.state[("doc", space_id, "docs/page.md", snapshot_sha)] = "content"

        build_resp = client.post(
            "/api/kb/v1/index/build",
            json={"space_id": space_id, "snapshot_sha": snapshot_sha},
        )
        generation_id = build_resp.json()["generation_id"]

        # First activation uses fence_token 0 and creates token 1.
        r1 = client.post(
            "/api/kb/v1/index/activate",
            json={
                "space_id": space_id,
                "profile": "default",
                "generation_id": str(generation_id),
                "fence_token": 0,
            },
        )
        assert r1.status_code == 200

        # Re-activating the same generation with the old token must conflict.
        r2 = client.post(
            "/api/kb/v1/index/activate",
            json={
                "space_id": space_id,
                "profile": "default",
                "generation_id": str(generation_id),
                "fence_token": 0,
            },
        )
        assert r2.status_code == 409
        assert r2.json()["detail"]["code"] == "INDEX_GENERATION_CONFLICT"


class TestSearch:
    def test_search_not_ready_without_active_pointer(
        self,
        client: TestClient,
        space_id: str,
        actor_id: uuid.UUID,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/search",
            json={
                "space_id": space_id,
                "query": "anything",
                "actor_id": str(actor_id),
                "profile": "default",
            },
        )
        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "INDEX_NOT_READY"

    def test_search_filters_unauthorized_payloads(
        self,
        client: TestClient,
        go_client: StubGOClient,
        identity_client: StubIdentityClient,
        space_id: str,
        snapshot_sha: str,
        actor_id: uuid.UUID,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/public.md", "type": "blob", "sha": "b" * 40},
            {"path": "secret/internal.md", "type": "blob", "sha": "c" * 40},
        ]
        go_client.state[("doc", space_id, "docs/public.md", snapshot_sha)] = (
            "Public retrieval documentation."
        )
        go_client.state[("doc", space_id, "secret/internal.md", snapshot_sha)] = (
            "Internal secret retrieval documentation."
        )

        build_resp = client.post(
            "/api/kb/v1/index/build",
            json={"space_id": space_id, "snapshot_sha": snapshot_sha},
        )
        generation_id = build_resp.json()["generation_id"]

        client.post(
            "/api/kb/v1/index/activate",
            json={
                "space_id": space_id,
                "profile": "default",
                "generation_id": str(generation_id),
                "fence_token": 0,
            },
        )

        # Deny paths under /secret.
        identity_client.allowed_prefixes = ["/docs"]

        resp = client.post(
            "/api/kb/v1/search",
            json={
                "space_id": space_id,
                "query": "documentation",
                "actor_id": str(actor_id),
                "profile": "default",
                "mode": "hybrid",
                "top_k": 10,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        paths = {r["document_path"] for r in body["results"]}
        assert "docs/public.md" in paths
        assert "secret/internal.md" not in paths

    def test_search_exact_mode(
        self,
        client: TestClient,
        go_client: StubGOClient,
        space_id: str,
        snapshot_sha: str,
        actor_id: uuid.UUID,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/alpha.md", "type": "blob", "sha": "b" * 40},
            {"path": "docs/beta.md", "type": "blob", "sha": "c" * 40},
        ]
        go_client.state[("doc", space_id, "docs/alpha.md", snapshot_sha)] = (
            "Alpha contains the target keyword."
        )
        go_client.state[("doc", space_id, "docs/beta.md", snapshot_sha)] = (
            "Beta has unrelated content."
        )

        build_resp = client.post(
            "/api/kb/v1/index/build",
            json={"space_id": space_id, "snapshot_sha": snapshot_sha},
        )
        generation_id = build_resp.json()["generation_id"]

        client.post(
            "/api/kb/v1/index/activate",
            json={
                "space_id": space_id,
                "profile": "default",
                "generation_id": str(generation_id),
                "fence_token": 0,
            },
        )

        resp = client.post(
            "/api/kb/v1/search",
            json={
                "space_id": space_id,
                "query": "target keyword",
                "actor_id": str(actor_id),
                "profile": "default",
                "mode": "exact",
                "top_k": 10,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        paths = {r["document_path"] for r in body["results"]}
        assert "docs/alpha.md" in paths
        assert "docs/beta.md" not in paths


class TestSearchLog:
    def test_search_creates_audit_log(
        self,
        client: TestClient,
        go_client: StubGOClient,
        space_id: str,
        snapshot_sha: str,
        actor_id: uuid.UUID,
        db_session: Any,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/page.md", "type": "blob", "sha": "b" * 40},
        ]
        go_client.state[("doc", space_id, "docs/page.md", snapshot_sha)] = (
            "Search audit log test document."
        )

        build_resp = client.post(
            "/api/kb/v1/index/build",
            json={"space_id": space_id, "snapshot_sha": snapshot_sha},
        )
        generation_id = build_resp.json()["generation_id"]

        client.post(
            "/api/kb/v1/index/activate",
            json={
                "space_id": space_id,
                "profile": "default",
                "generation_id": str(generation_id),
                "fence_token": 0,
            },
        )

        resp = client.post(
            "/api/kb/v1/search",
            json={
                "space_id": space_id,
                "query": "audit log",
                "actor_id": str(actor_id),
                "profile": "default",
            },
        )
        assert resp.status_code == 200

        from retrieval.app.models.index import SearchLog

        logs = db_session.query(SearchLog).all()
        assert len(logs) == 1
        assert logs[0].space_id == space_id
        assert logs[0].query == "audit log"
        assert logs[0].actor_id == str(actor_id)


class _RaisingEmbeddingAdapter(EmbeddingAdapter):
    def __init__(self, exception: Exception | None = None) -> None:
        self.exception = exception or EmbeddingAdapterError("adapter failed")

    def encode(self, texts: list[str]) -> list[list[float]]:
        raise self.exception


class _WrongCountEmbeddingAdapter(EmbeddingAdapter):
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384]


class _RaisingIdentityClient(StubIdentityClient):
    def check_path(
        self,
        space_id: str,
        actor_id: uuid.UUID,
        path: str,
    ) -> dict[str, Any]:
        raise IdentityClientError("identity unavailable")


class TestCosineSimilarity:
    def test_cosine_similarity_normalizes_non_unit_vectors(self) -> None:
        a = [3.0, 4.0]
        b = [6.0, 8.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_cosine_similarity_opposite_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_cosine_similarity_mismatched_length_returns_zero(self) -> None:
        assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_cosine_similarity_empty_vectors_return_zero(self) -> None:
        assert cosine_similarity([], []) == 0.0


class TestHybridRanking:
    def test_hybrid_ranking_prefers_semantic_and_exact_match(self) -> None:
        from retrieval.app.models.index import Chunk
        from retrieval.app.services.search import _rank_chunks

        chunk_a = Chunk(
            id=uuid.uuid4(),
            document_path="docs/alpha.md",
            content="exact keyword match semantic overlap",
            embedding=[1.0, 0.0],
        )
        chunk_b = Chunk(
            id=uuid.uuid4(),
            document_path="docs/beta.md",
            content="exact keyword match only",
            embedding=[0.0, 1.0],
        )
        chunk_c = Chunk(
            id=uuid.uuid4(),
            document_path="docs/gamma.md",
            content="unrelated sports content",
            embedding=[0.0, 0.0],
        )

        ranked = _rank_chunks(
            [chunk_a, chunk_b, chunk_c],
            "exact keyword match",
            [1.0, 0.0],
            "hybrid",
        )
        paths = [chunk.document_path for chunk, _score, _mode in ranked]
        assert paths[0] == "docs/alpha.md"
        assert "docs/beta.md" in paths
        assert "docs/gamma.md" not in paths


class TestEmbeddingAdapterFactory:
    def test_build_stub_adapter(self) -> None:
        class _Settings:
            EMBEDDING_MODEL = "stub-deterministic"
            EMBEDDING_DIMENSIONS = 128

        adapter = build_embedding_adapter(_Settings())
        assert isinstance(adapter, StubEmbeddingAdapter)
        assert adapter.dimensions == 128

    def test_build_production_adapter(self) -> None:
        class _Settings:
            EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
            EMBEDDING_DIMENSIONS = 384

        adapter = build_embedding_adapter(_Settings())
        assert isinstance(adapter, ProductionEmbeddingAdapter)
        assert adapter.model == "sentence-transformers/all-MiniLM-L6-v2"
        assert adapter.dimensions == 384


class TestBuildIndexErrors:
    def test_build_index_raises_upstream_unavailable_on_embedding_error(
        self,
        db_session: Any,
        go_client: StubGOClient,
        space_id: str,
        snapshot_sha: str,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/page.md", "type": "blob", "sha": "b" * 40},
        ]
        go_client.state[("doc", space_id, "docs/page.md", snapshot_sha)] = (
            "Document that will fail embedding."
        )

        failing_adapter = _RaisingEmbeddingAdapter()

        with pytest.raises(RetrievalServiceError) as exc_info:
            build_index(db_session, go_client, failing_adapter, space_id, snapshot_sha)
        assert exc_info.value.code == "UPSTREAM_UNAVAILABLE"
        assert "embedding" in exc_info.value.message.lower()

    def test_build_index_raises_on_embedding_count_mismatch(
        self,
        db_session: Any,
        go_client: StubGOClient,
        space_id: str,
        snapshot_sha: str,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/a.md", "type": "blob", "sha": "b" * 40},
            {"path": "docs/b.md", "type": "blob", "sha": "c" * 40},
        ]
        go_client.state[("doc", space_id, "docs/a.md", snapshot_sha)] = "First document."
        go_client.state[("doc", space_id, "docs/b.md", snapshot_sha)] = "Second document."

        wrong_adapter = _WrongCountEmbeddingAdapter()

        with pytest.raises(RetrievalServiceError) as exc_info:
            build_index(db_session, go_client, wrong_adapter, space_id, snapshot_sha)
        assert exc_info.value.code == "UPSTREAM_UNAVAILABLE"


class TestActivatePointerPromotion:
    def test_normal_pointer_promotion_to_new_generation(
        self,
        db_session: Any,
        go_client: StubGOClient,
        embedding_adapter: StubEmbeddingAdapter,
        space_id: str,
        snapshot_sha: str,
    ) -> None:
        sha_a = snapshot_sha
        sha_b = "b" * 40

        go_client.state[("tree", space_id, sha_a)] = [
            {"path": "docs/v1.md", "type": "blob", "sha": "a" * 40},
        ]
        go_client.state[("doc", space_id, "docs/v1.md", sha_a)] = "Version one."

        go_client.state[("tree", space_id, sha_b)] = [
            {"path": "docs/v2.md", "type": "blob", "sha": "b" * 40},
        ]
        go_client.state[("doc", space_id, "docs/v2.md", sha_b)] = "Version two."

        gen1 = build_index(db_session, go_client, embedding_adapter, space_id, sha_a)
        pointer1 = activate_pointer(db_session, space_id, "default", gen1.id, 0)
        assert pointer1.fence_token == 1

        gen2 = build_index(db_session, go_client, embedding_adapter, space_id, sha_b)
        pointer2 = activate_pointer(db_session, space_id, "default", gen2.id, pointer1.fence_token)
        assert pointer2.fence_token == 2
        assert pointer2.generation_id == gen2.id


class TestActivatePointerLocking:
    def test_activate_pointer_query_uses_row_level_locking(self) -> None:
        from sqlalchemy.dialects.postgresql import dialect as pg_dialect
        from sqlalchemy.orm import Session

        from retrieval.app.models.index import IndexPointer

        engine = create_engine("sqlite:///:memory:")
        session = Session(engine)
        query = (
            session.query(IndexPointer)
            .filter(
                IndexPointer.space_id == "s",
                IndexPointer.profile == "p",
                IndexPointer.active.is_(True),
            )
            .with_for_update()
        )
        compiled = query.statement.compile(dialect=pg_dialect())
        assert "FOR UPDATE" in str(compiled)

    def test_concurrent_activation_maintains_single_active_pointer(
        self,
        go_client: StubGOClient,
        identity_client: StubIdentityClient,
        embedding_adapter: StubEmbeddingAdapter,
        space_id: str,
        snapshot_sha: str,
    ) -> None:
        import tempfile
        import threading

        from sqlalchemy.orm import sessionmaker

        from retrieval.app.main import create_app
        from retrieval.app.models.index import Base, IndexPointer
        from retrieval.app.repositories.db import get_db

        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db_url = f"sqlite:///{tmp.name}"
            engine = create_engine(db_url)
            Base.metadata.create_all(engine)

            SessionLocal = sessionmaker(bind=engine)

            app = create_app(
                identity_client=identity_client,
                go_client=go_client,
                embedding_adapter=embedding_adapter,
            )

            async def _override_get_db() -> AsyncGenerator[Any, None]:
                session = SessionLocal()
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

            app.dependency_overrides[get_db] = _override_get_db

            sha_a = snapshot_sha
            sha_b = "b" * 40
            go_client.state[("tree", space_id, sha_a)] = [
                {"path": "docs/v1.md", "type": "blob", "sha": "a" * 40},
            ]
            go_client.state[("doc", space_id, "docs/v1.md", sha_a)] = "Version one."
            go_client.state[("tree", space_id, sha_b)] = [
                {"path": "docs/v2.md", "type": "blob", "sha": "b" * 40},
            ]
            go_client.state[("doc", space_id, "docs/v2.md", sha_b)] = "Version two."

            with TestClient(app) as c:
                gen1_resp = c.post(
                    "/api/kb/v1/index/build",
                    json={"space_id": space_id, "snapshot_sha": sha_a},
                )
                gen1_id = gen1_resp.json()["generation_id"]
                c.post(
                    "/api/kb/v1/index/activate",
                    json={
                        "space_id": space_id,
                        "profile": "default",
                        "generation_id": str(gen1_id),
                        "fence_token": 0,
                    },
                )

                gen2_resp = c.post(
                    "/api/kb/v1/index/build",
                    json={"space_id": space_id, "snapshot_sha": sha_b},
                )
                gen2_id = gen2_resp.json()["generation_id"]

            results: list[int] = []

            def activate(client: TestClient, generation_id: uuid.UUID, fence_token: int) -> None:
                resp = client.post(
                    "/api/kb/v1/index/activate",
                    json={
                        "space_id": space_id,
                        "profile": "default",
                        "generation_id": str(generation_id),
                        "fence_token": fence_token,
                    },
                )
                results.append(resp.status_code)

            with TestClient(app) as c1, TestClient(app) as c2:
                t1 = threading.Thread(target=activate, args=(c1, gen2_id, 1))
                t2 = threading.Thread(target=activate, args=(c2, gen2_id, 1))
                t1.start()
                t2.start()
                t1.join()
                t2.join()

            with SessionLocal() as check_session:
                active = (
                    check_session.query(IndexPointer)
                    .filter(
                        IndexPointer.space_id == space_id,
                        IndexPointer.profile == "default",
                        IndexPointer.active.is_(True),
                    )
                    .all()
                )
                assert len(active) == 1
                assert str(active[0].generation_id) == str(gen2_id)

            assert 200 in results
            assert all(code in {200, 409} for code in results)


class TestSearchErrors:
    def test_search_raises_upstream_unavailable_on_embedding_error(
        self,
        db_session: Any,
        go_client: StubGOClient,
        identity_client: StubIdentityClient,
        embedding_adapter: StubEmbeddingAdapter,
        space_id: str,
        snapshot_sha: str,
        actor_id: uuid.UUID,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/page.md", "type": "blob", "sha": "b" * 40},
        ]
        go_client.state[("doc", space_id, "docs/page.md", snapshot_sha)] = "Content."

        generation = build_index(db_session, go_client, embedding_adapter, space_id, snapshot_sha)
        activate_pointer(db_session, space_id, "default", generation.id, 0)
        db_session.commit()

        failing_adapter = _RaisingEmbeddingAdapter()

        from retrieval.app.services import search as search_module

        with pytest.raises(RetrievalServiceError) as exc_info:
            search_module.search(
                db_session,
                identity_client,
                failing_adapter,
                space_id,
                "query",
                actor_id,
                mode="semantic",
            )
        assert exc_info.value.code == "UPSTREAM_UNAVAILABLE"
        assert "embedding" in exc_info.value.message.lower()

    def test_search_raises_upstream_unavailable_on_identity_error(
        self,
        db_session: Any,
        go_client: StubGOClient,
        embedding_adapter: StubEmbeddingAdapter,
        space_id: str,
        snapshot_sha: str,
        actor_id: uuid.UUID,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/page.md", "type": "blob", "sha": "b" * 40},
        ]
        go_client.state[("doc", space_id, "docs/page.md", snapshot_sha)] = "Content."

        generation = build_index(db_session, go_client, embedding_adapter, space_id, snapshot_sha)
        activate_pointer(db_session, space_id, "default", generation.id, 0)
        db_session.commit()

        failing_identity = _RaisingIdentityClient()

        from retrieval.app.services import search as search_module

        with pytest.raises(RetrievalServiceError) as exc_info:
            search_module.search(
                db_session,
                failing_identity,
                embedding_adapter,
                space_id,
                "content",
                actor_id,
            )
        assert exc_info.value.code == "UPSTREAM_UNAVAILABLE"
        assert "identity" in exc_info.value.message.lower()


class TestSearchFilteredContract:
    def test_all_results_filtered_returns_empty_with_count(
        self,
        client: TestClient,
        go_client: StubGOClient,
        identity_client: StubIdentityClient,
        space_id: str,
        snapshot_sha: str,
        actor_id: uuid.UUID,
    ) -> None:
        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "secret/a.md", "type": "blob", "sha": "b" * 40},
            {"path": "secret/b.md", "type": "blob", "sha": "c" * 40},
        ]
        go_client.state[("doc", space_id, "secret/a.md", snapshot_sha)] = (
            "Secret document one."
        )
        go_client.state[("doc", space_id, "secret/b.md", snapshot_sha)] = (
            "Secret document two."
        )

        build_resp = client.post(
            "/api/kb/v1/index/build",
            json={"space_id": space_id, "snapshot_sha": snapshot_sha},
        )
        generation_id = build_resp.json()["generation_id"]

        client.post(
            "/api/kb/v1/index/activate",
            json={
                "space_id": space_id,
                "profile": "default",
                "generation_id": str(generation_id),
                "fence_token": 0,
            },
        )

        identity_client.allowed_prefixes = ["/docs"]

        resp = client.post(
            "/api/kb/v1/search",
            json={
                "space_id": space_id,
                "query": "secret document",
                "actor_id": str(actor_id),
                "profile": "default",
                "mode": "exact",
                "top_k": 10,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["results"] == []
        assert body["authorization_filtered_count"] == 2


class TestSearchVectorIndex:
    def test_semantic_search_query_uses_vector_distance_on_postgresql(self) -> None:
        from sqlalchemy.dialects.postgresql import dialect as pg_dialect
        from sqlalchemy.orm import Session

        from retrieval.app.models.index import Chunk
        from retrieval.app.services.search import QUERY_CHUNK_LIMIT

        engine = create_engine("sqlite:///:memory:")
        session = Session(engine)
        query = (
            session.query(Chunk)
            .filter(Chunk.generation_id == "generation-id")
            .order_by(Chunk.embedding.op("<=>")([1.0, 0.0]))
            .limit(QUERY_CHUNK_LIMIT)
        )
        compiled = query.statement.compile(dialect=pg_dialect())
        sql = str(compiled)
        assert "<=>" in sql
        assert "ORDER BY" in sql
        assert "LIMIT" in sql


class TestSearchChunkLimit:
    def test_search_respects_chunk_query_limit(
        self,
        monkeypatch: Any,
        db_session: Any,
        go_client: StubGOClient,
        identity_client: StubIdentityClient,
        embedding_adapter: StubEmbeddingAdapter,
        space_id: str,
        snapshot_sha: str,
        actor_id: uuid.UUID,
    ) -> None:
        from retrieval.app.services import search as search_module

        monkeypatch.setattr(search_module, "QUERY_CHUNK_LIMIT", 2)

        go_client.state[("tree", space_id, snapshot_sha)] = [
            {"path": "docs/a.md", "type": "blob", "sha": "a" * 40},
            {"path": "docs/b.md", "type": "blob", "sha": "b" * 40},
            {"path": "docs/c.md", "type": "blob", "sha": "c" * 40},
        ]
        go_client.state[("doc", space_id, "docs/a.md", snapshot_sha)] = "alpha"
        go_client.state[("doc", space_id, "docs/b.md", snapshot_sha)] = "beta"
        go_client.state[("doc", space_id, "docs/c.md", snapshot_sha)] = "gamma"

        generation = build_index(db_session, go_client, embedding_adapter, space_id, snapshot_sha)
        activate_pointer(db_session, space_id, "default", generation.id, 0)
        db_session.commit()

        response = search_module.search(
            db_session,
            identity_client,
            embedding_adapter,
            space_id,
            "alpha beta gamma",
            actor_id,
            mode="exact",
            top_k=10,
        )
        assert len(response["results"]) <= 2
