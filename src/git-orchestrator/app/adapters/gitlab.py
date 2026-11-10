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
        merge_commit_message: str | None = None,
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

    @abstractmethod
    def create_note(
        self,
        space_id: str,
        mr_iid: int,
        body: str,
    ) -> dict[str, Any]:
        """Create a structured MR note and return its metadata."""

    @abstractmethod
    def create_tag(
        self,
        space_id: str,
        tag_name: str,
        ref: str,
        message: str,
    ) -> dict[str, Any]:
        """Create a protected annotated tag pointing at ``ref``."""

    @abstractmethod
    def get_commit(self, space_id: str, sha: str) -> dict[str, Any]:
        """Return commit metadata including parent SHAs."""

    @abstractmethod
    def get_branch(self, space_id: str, branch: str) -> dict[str, Any]:
        """Return branch metadata including HEAD commit SHA."""


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
        merge_commit_message: str | None = None,
    ) -> dict[str, Any]:
        import httpx

        url = f"{self._project_url(space_id)}/merge_requests/{mr_iid}/merge"
        payload: dict[str, Any] = {
            "sha": sha,
            "should_remove_source_branch": False,
        }
        if merge_commit_message is not None:
            payload["merge_commit_message"] = merge_commit_message
        response = httpx.put(
            url,
            headers=self._headers(),
            json=payload,
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
                level["access_level"] == 40 for level in data.get("merge_access_levels", [])
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

    def create_note(
        self,
        space_id: str,
        mr_iid: int,
        body: str,
    ) -> dict[str, Any]:
        import httpx

        url = f"{self._project_url(space_id)}/merge_requests/{mr_iid}/notes"
        response = httpx.post(
            url,
            headers=self._headers(),
            json={"body": body},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def create_tag(
        self,
        space_id: str,
        tag_name: str,
        ref: str,
        message: str,
    ) -> dict[str, Any]:
        import httpx

        url = f"{self._project_url(space_id)}/repository/tags"
        response = httpx.post(
            url,
            headers=self._headers(),
            json={
                "tag_name": tag_name,
                "ref": ref,
                "message": message,
            },
            timeout=30,
        )
        response.raise_for_status()
        tag = response.json()

        # Protect the annotated tag so it cannot be moved/deleted by
        # non-maintainers (G1 requirement: protected kb-decisions/* tags).
        protected_url = f"{self._project_url(space_id)}/protected_tags"
        protected_response = httpx.post(
            protected_url,
            headers=self._headers(),
            json={
                "name": tag_name,
                "create_access_levels": [{"access_level": 40}],
            },
            timeout=30,
        )
        protected_response.raise_for_status()
        verification = httpx.get(
            f"{protected_url}/{quote(tag_name, safe='')}",
            headers=self._headers(),
            timeout=30,
        )
        verification.raise_for_status()
        if verification.json().get("name") not in {tag_name, "kb-decisions/*"}:
            raise GitLabAdapterError(f"tag protection missing for {tag_name}")

        return tag

    def get_commit(self, space_id: str, sha: str) -> dict[str, Any]:
        import httpx

        url = f"{self._project_url(space_id)}/repository/commits/{sha}"
        response = httpx.get(url, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def get_branch(self, space_id: str, branch: str) -> dict[str, Any]:
        import httpx

        url = f"{self._project_url(space_id)}/repository/branches/{quote(branch, safe='')}"
        response = httpx.get(url, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()


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
        merge_commit_message: str | None = None,
    ) -> dict[str, Any]:
        if self.state.get(("merge_fail", space_id, mr_iid)):
            raise GitLabAdapterError("merge failed")
        mr = self.get_merge_request(space_id, mr_iid)
        mr["state"] = "merged"
        mr["sha"] = sha
        if merge_commit_message is not None:
            mr["merge_commit_message"] = merge_commit_message
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

    def create_note(
        self,
        space_id: str,
        mr_iid: int,
        body: str,
    ) -> dict[str, Any]:
        note_id = len([k for k in self.state if k[0] == "note"]) + 1
        note = {"id": note_id, "body": body, "mr_iid": mr_iid}
        self.state[("note", space_id, mr_iid, note_id)] = note
        return note

    def create_tag(
        self,
        space_id: str,
        tag_name: str,
        ref: str,
        message: str,
    ) -> dict[str, Any]:
        tag = {"name": tag_name, "target": ref, "message": message}
        self.state[("tag", space_id, tag_name)] = tag
        return tag

    def get_commit(self, space_id: str, sha: str) -> dict[str, Any]:
        commit = self._get(("commit", space_id, sha), {})
        return dict(commit)

    def get_branch(self, space_id: str, branch: str) -> dict[str, Any]:
        branch_data = self._get(
            ("branch", space_id, branch),
            {"name": branch, "commit": {"id": ""}},
        )
        return dict(branch_data)
