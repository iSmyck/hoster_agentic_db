"""GitLab adapter interface, HTTP implementation, and test stub."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import quote


class GitLabAdapterError(Exception):
    """Raised when a GitLab adapter operation fails."""


class GitLabAdapter(ABC):
    """Outbound port for GitLab interactions."""

    @abstractmethod
    def get_tree(self, space_id: str, sha: str) -> list[dict[str, Any]]:
        """Return a tree listing for the given Space/repository at ``sha``."""

    @abstractmethod
    def read_document(self, space_id: str, path: str, sha: str) -> str:
        """Return the decoded text content of ``path`` at ``sha``."""

    @abstractmethod
    def get_merge_request(self, space_id: str, mr_iid: int) -> dict[str, Any]:
        """Return MR metadata for ``mr_iid``."""

    @abstractmethod
    def create_merge_request(
        self,
        space_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
    ) -> dict[str, Any]:
        """Create an MR and return its metadata."""

    @abstractmethod
    def merge_merge_request(
        self,
        space_id: str,
        mr_iid: int,
        sha: str,
    ) -> dict[str, Any]:
        """Apply the MR merge and return merge metadata."""

    @abstractmethod
    def protected_branch_rules(self, space_id: str) -> dict[str, Any]:
        """Return protected-branch rules for the Space target branch."""

    @abstractmethod
    def direct_push_check(self, space_id: str) -> bool:
        """Return ``True`` if direct push into the protected target is blocked."""

    @abstractmethod
    def branch_exists(self, space_id: str, branch: str) -> bool:
        """Return ``True`` if ``branch`` exists in the Space repository."""


class HttpGitLabAdapter(GitLabAdapter):
    """Production adapter using the GitLab REST API via httpx.

    ``httpx`` is imported lazily inside methods so the module can be imported
    in environments where only the stub adapter is used.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        project_path_prefix: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.project_path_prefix = project_path_prefix

    def _project_path(self, space_id: str) -> str:
        return f"{self.project_path_prefix}{space_id}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _project_url(self, space_id: str) -> str:
        return f"{self.base_url}/api/v4/projects/{quote(self._project_path(space_id), safe='')}"

    def get_tree(self, space_id: str, sha: str) -> list[dict[str, Any]]:
        import httpx

        url = f"{self._project_url(space_id)}/repository/tree"
        results: list[dict[str, Any]] = []
        page = 1
        per_page = 100
        while True:
            response = httpx.get(
                url,
                headers=self._headers(),
                params={"ref": sha, "per_page": per_page, "page": page},
                timeout=30,
            )
            response.raise_for_status()
            page_data = response.json()
            results.extend(page_data)
            if len(page_data) < per_page:
                break
            page += 1
        return results

    def read_document(self, space_id: str, path: str, sha: str) -> str:
        import httpx

        url = f"{self._project_url(space_id)}/repository/files/{quote(path, safe='')}/raw"
        response = httpx.get(
            url,
            headers=self._headers(),
            params={"ref": sha},
            timeout=30,
        )
        response.raise_for_status()
        return response.text

    def get_merge_request(self, space_id: str, mr_iid: int) -> dict[str, Any]:
        import httpx

        url = f"{self._project_url(space_id)}/merge_requests/{mr_iid}"
        response = httpx.get(url, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def create_merge_request(
        self,
        space_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
    ) -> dict[str, Any]:
        import httpx

        url = f"{self._project_url(space_id)}/merge_requests"
        response = httpx.post(
            url,
            headers=self._headers(),
            json={
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def merge_merge_request(
        self,
        space_id: str,
        mr_iid: int,
        sha: str,
    ) -> dict[str, Any]:
        import httpx

        url = f"{self._project_url(space_id)}/merge_requests/{mr_iid}/merge"
        response = httpx.put(
            url,
            headers=self._headers(),
            json={
                "sha": sha,
                "should_remove_source_branch": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def protected_branch_rules(self, space_id: str) -> dict[str, Any]:
        import httpx

        # MVP assumes the protected target branch is named "main".
        url = f"{self._project_url(space_id)}/protected_branches/main"
        response = httpx.get(url, headers=self._headers(), timeout=30)
        if response.status_code == 404:
            return {"protected": False, "merge_only": False}
        response.raise_for_status()
        data = response.json()
        return {
            "protected": True,
            "merge_only": all(
                level["access_level"] == 40
                for level in data.get("merge_access_levels", [])
            ),
            "push_access_levels": data.get("push_access_levels", []),
            "merge_access_levels": data.get("merge_access_levels", []),
        }

    def direct_push_check(self, space_id: str) -> bool:
        rules = self.protected_branch_rules(space_id)
        return bool(rules.get("protected")) and bool(rules.get("merge_only"))

    def branch_exists(self, space_id: str, branch: str) -> bool:
        import httpx

        url = f"{self._project_url(space_id)}/repository/branches/{quote(branch, safe='')}"
        response = httpx.get(url, headers=self._headers(), timeout=30)
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True


class StubGitLabAdapter(GitLabAdapter):
    """In-memory stub for unit tests. No external calls."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = state or {}
        self._mr_counter = 0

    def _get(self, key: tuple[Any, ...], default: Any) -> Any:
        return self.state.get(key, default)

    def get_tree(self, space_id: str, sha: str) -> list[dict[str, Any]]:
        return list(self._get(("tree", space_id, sha), []))

    def read_document(self, space_id: str, path: str, sha: str) -> str:
        return str(self._get(("doc", space_id, path, sha), ""))

    def get_merge_request(self, space_id: str, mr_iid: int) -> dict[str, Any]:
        mr = self._get(("mr", space_id, mr_iid), {"iid": mr_iid, "state": "opened"})
        return dict(mr)

    def create_merge_request(
        self,
        space_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
    ) -> dict[str, Any]:
        if self.state.get(("mr_create_fail", space_id)):
            raise GitLabAdapterError("create merge request failed")
        self._mr_counter += 1
        mr = {
            "iid": self._mr_counter,
            "space_id": space_id,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "state": "opened",
            "base_sha": self.state.get(("base_sha", space_id), ""),
        }
        self.state[("mr", space_id, self._mr_counter)] = mr
        return mr

    def merge_merge_request(
        self,
        space_id: str,
        mr_iid: int,
        sha: str,
    ) -> dict[str, Any]:
        if self.state.get(("merge_fail", space_id, mr_iid)):
            raise GitLabAdapterError("merge failed")
        mr = self.get_merge_request(space_id, mr_iid)
        mr["state"] = "merged"
        mr["sha"] = sha
        self.state[("mr", space_id, mr_iid)] = mr
        return mr

    def protected_branch_rules(self, space_id: str) -> dict[str, Any]:
        return dict(
            self._get(
                ("rules", space_id),
                {"protected": True, "merge_only": True, "push_access_levels": []},
            )
        )

    def direct_push_check(self, space_id: str) -> bool:
        return bool(self.state.get(("direct_push_ok", space_id), True))

    def branch_exists(self, space_id: str, branch: str) -> bool:
        return bool(self._get(("branch", space_id, branch), True))
