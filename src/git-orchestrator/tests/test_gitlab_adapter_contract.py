"""Contract tests for HttpGitLabAdapter using httpx.MockTransport."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest import mock
from urllib.parse import quote

import httpx
import pytest
from git_orchestrator.app.adapters.gitlab import HttpGitLabAdapter

BASE_URL = "https://gitlab.example.com"
TOKEN = "test-token"
SPACE_ID = "demo/space"
ENCODED_SPACE = quote(SPACE_ID, safe="")
PROJECT_PATH = f"/api/v4/projects/{SPACE_ID}"
PROJECT_URL = f"{BASE_URL}/api/v4/projects/{ENCODED_SPACE}"


@contextmanager
def _mock_httpx(transport: httpx.MockTransport) -> Generator[None, None, None]:
    """Patch the top-level httpx functions to use a client with ``transport``."""
    with (
        httpx.Client(transport=transport) as client, mock.patch("httpx.get", client.get),
        mock.patch("httpx.post", client.post),
        mock.patch("httpx.put", client.put),
    ):
        yield


def _make_handler(responses: dict[str, Any]) -> Any:
    """Return an httpx MockTransport handler driven by ``responses``.

    Keys are ``"{METHOD} {path}"`` where path is the URL-decoded path suffix
    after ``/api/v4/projects/{space_id}``. Values are either a response body
    (dict/list/str) or a tuple ``(status_code, body)``.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        suffix = request.url.path.split(PROJECT_PATH)[-1]
        key = f"{request.method} {suffix}"
        match = responses.get(key)
        if match is None:
            return httpx.Response(404, text="not found")

        if isinstance(match, tuple):
            status_code, body = match
        else:
            status_code, body = 200, match

        if isinstance(body, (dict, list)):
            return httpx.Response(status_code, json=body)
        return httpx.Response(status_code, text=body)

    return handler


@pytest.fixture
def adapter() -> HttpGitLabAdapter:
    return HttpGitLabAdapter(BASE_URL, TOKEN)


class TestGetTree:
    def test_get_tree_single_page(self, adapter: HttpGitLabAdapter) -> None:
        tree = [
            {"path": "docs", "type": "tree", "sha": "d" * 40, "mode": "040000"},
            {"path": "docs/page.md", "type": "blob", "sha": "e" * 40, "mode": "100644"},
        ]
        transport = httpx.MockTransport(_make_handler({"GET /repository/tree": tree}))

        with _mock_httpx(transport):
            result = adapter.get_tree(SPACE_ID, "a" * 40)

        assert result == tree

    def test_get_tree_paginates(self, adapter: HttpGitLabAdapter) -> None:
        page1 = [
            {"path": f"f{i}.md", "type": "blob", "sha": "a" * 40, "mode": "100644"}
            for i in range(100)
        ]
        page2 = [{"path": "last.md", "type": "blob", "sha": "b" * 40, "mode": "100644"}]

        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            page = request.url.params.get("page")
            if page == "1":
                return httpx.Response(200, json=page1)
            if page == "2":
                return httpx.Response(200, json=page2)
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        with _mock_httpx(transport):
            result = adapter.get_tree(SPACE_ID, "a" * 40)

        assert len(result) == 101
        assert result[0]["path"] == "f0.md"
        assert result[-1]["path"] == "last.md"
        assert len(requests) == 2
        assert requests[0].url.params["per_page"] == "100"
        assert requests[1].url.params["per_page"] == "100"


class TestReadDocument:
    def test_read_document_success(self, adapter: HttpGitLabAdapter) -> None:
        transport = httpx.MockTransport(
            _make_handler({"GET /repository/files/docs/page.md/raw": "hello"})
        )

        with _mock_httpx(transport):
            result = adapter.read_document(SPACE_ID, "docs/page.md", "a" * 40)

        assert result == "hello"

    def test_read_document_not_found(self, adapter: HttpGitLabAdapter) -> None:
        transport = httpx.MockTransport(
            _make_handler(
                {
                    "GET /repository/files/missing.md/raw": (
                        404,
                        "404 File Not Found",
                    ),
                }
            )
        )

        with _mock_httpx(transport), pytest.raises(httpx.HTTPStatusError):
            adapter.read_document(SPACE_ID, "missing.md", "a" * 40)


class TestMergeRequest:
    def test_get_merge_request(self, adapter: HttpGitLabAdapter) -> None:
        mr = {"iid": 42, "state": "opened", "title": "Test MR"}
        transport = httpx.MockTransport(_make_handler({"GET /merge_requests/42": mr}))

        with _mock_httpx(transport):
            result = adapter.get_merge_request(SPACE_ID, 42)

        assert result == mr

    def test_create_merge_request(self, adapter: HttpGitLabAdapter) -> None:
        mr = {"iid": 1, "state": "opened", "title": "Proposal aaaaaaaa"}
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(201, json=mr)

        transport = httpx.MockTransport(handler)
        with _mock_httpx(transport):
            result = adapter.create_merge_request(
                SPACE_ID, "proposal/aaaaaaaa", "main", "Proposal aaaaaaaa"
            )

        assert result == mr
        assert len(requests) == 1
        body = requests[0].read()
        assert b"proposal/aaaaaaaa" in body
        assert b"main" in body

    def test_merge_merge_request(self, adapter: HttpGitLabAdapter) -> None:
        merged = {"iid": 1, "state": "merged", "sha": "a" * 40}
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=merged)

        transport = httpx.MockTransport(handler)
        with _mock_httpx(transport):
            result = adapter.merge_merge_request(SPACE_ID, 1, "a" * 40)

        assert result == merged
        assert requests[0].url.path.endswith("/merge_requests/1/merge")


class TestProtectedBranchRules:
    def test_protected_branch_rules_merge_only(self, adapter: HttpGitLabAdapter) -> None:
        rules = {
            "push_access_levels": [{"access_level": 30}],
            "merge_access_levels": [{"access_level": 40}],
        }
        transport = httpx.MockTransport(_make_handler({"GET /protected_branches/main": rules}))

        with _mock_httpx(transport):
            result = adapter.protected_branch_rules(SPACE_ID)

        assert result["protected"] is True
        assert result["merge_only"] is True
        assert result["push_access_levels"] == [{"access_level": 30}]

    def test_protected_branch_rules_not_merge_only(self, adapter: HttpGitLabAdapter) -> None:
        rules = {
            "push_access_levels": [{"access_level": 40}],
            "merge_access_levels": [{"access_level": 30}, {"access_level": 40}],
        }
        transport = httpx.MockTransport(_make_handler({"GET /protected_branches/main": rules}))

        with _mock_httpx(transport):
            result = adapter.protected_branch_rules(SPACE_ID)

        assert result["protected"] is True
        assert result["merge_only"] is False

    def test_protected_branch_rules_not_found(self, adapter: HttpGitLabAdapter) -> None:
        transport = httpx.MockTransport(
            _make_handler({"GET /protected_branches/main": (404, "not found")})
        )

        with _mock_httpx(transport):
            result = adapter.protected_branch_rules(SPACE_ID)

        assert result == {"protected": False, "merge_only": False}


class TestDirectPushCheck:
    def test_direct_push_blocked(self, adapter: HttpGitLabAdapter) -> None:
        rules = {
            "push_access_levels": [{"access_level": 30}],
            "merge_access_levels": [{"access_level": 40}],
        }
        transport = httpx.MockTransport(_make_handler({"GET /protected_branches/main": rules}))

        with _mock_httpx(transport):
            result = adapter.direct_push_check(SPACE_ID)

        assert result is True

    def test_direct_push_allowed(self, adapter: HttpGitLabAdapter) -> None:
        rules = {
            "push_access_levels": [{"access_level": 40}],
            "merge_access_levels": [{"access_level": 30}, {"access_level": 40}],
        }
        transport = httpx.MockTransport(_make_handler({"GET /protected_branches/main": rules}))

        with _mock_httpx(transport):
            result = adapter.direct_push_check(SPACE_ID)

        assert result is False


class TestBranchExists:
    def test_branch_exists_true(self, adapter: HttpGitLabAdapter) -> None:
        transport = httpx.MockTransport(
            _make_handler(
                {"GET /repository/branches/proposal/aaaaaaaa": {"name": "proposal/aaaaaaaa"}}
            )
        )

        with _mock_httpx(transport):
            result = adapter.branch_exists(SPACE_ID, "proposal/aaaaaaaa")

        assert result is True

    def test_branch_exists_false(self, adapter: HttpGitLabAdapter) -> None:
        transport = httpx.MockTransport(
            _make_handler(
                {"GET /repository/branches/proposal/aaaaaaaa": (404, "not found")}
            )
        )

        with _mock_httpx(transport):
            result = adapter.branch_exists(SPACE_ID, "proposal/aaaaaaaa")

        assert result is False
