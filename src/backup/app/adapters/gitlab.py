"""GitLab adapter for read-only backup metadata export."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import quote


class BackupGitLabAdapterError(Exception):
    """Raised when a backup GitLab adapter operation fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class BackupGitLabAdapter(ABC):
    """Outbound port for read-only GitLab interactions used by the backup service."""

    @abstractmethod
    def list_merge_requests(self, space_id: str) -> list[dict[str, Any]]:
        """Return all merge requests for the Space repository."""

    @abstractmethod
    def list_notes(self, space_id: str, mr_iid: int) -> list[dict[str, Any]]:
        """Return all notes for a merge request."""

    @abstractmethod
    def list_tags(self, space_id: str) -> list[dict[str, Any]]:
        """Return all tags for the Space repository."""

    @abstractmethod
    def get_project_url(self, space_id: str) -> str:
        """Return the human-readable GitLab project URL (without API path)."""

    @abstractmethod
    def get_branch(self, space_id: str, branch: str) -> dict[str, Any]:
        """Return branch metadata including HEAD commit SHA."""


class HttpBackupGitLabAdapter(BackupGitLabAdapter):
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
        return (
            f"{self.base_url}/api/v4/projects/{quote(self._project_path(space_id), safe='')}"
        )

    def _paginated_get(self, url: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        import httpx

        results: list[dict[str, Any]] = []
        page = 1
        per_page = 100
        while True:
            page_params = {"per_page": per_page, "page": page}
            if params:
                page_params.update(params)
            try:
                response = httpx.get(
                    url,
                    headers=self._headers(),
                    params=page_params,
                    timeout=30,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise BackupGitLabAdapterError(
                    f"GitLab request failed: {exc}",
                    status_code=exc.response.status_code,
                ) from exc
            page_data = response.json()
            if not isinstance(page_data, list):
                raise BackupGitLabAdapterError(
                    f"unexpected response shape from {url}: not a list"
                )
            results.extend(page_data)
            if len(page_data) < per_page:
                break
            page += 1
        return results

    def list_merge_requests(self, space_id: str) -> list[dict[str, Any]]:
        url = f"{self._project_url(space_id)}/merge_requests"
        return self._paginated_get(url, params={"state": "all"})

    def list_notes(self, space_id: str, mr_iid: int) -> list[dict[str, Any]]:
        url = f"{self._project_url(space_id)}/merge_requests/{mr_iid}/notes"
        return self._paginated_get(url)

    def list_tags(self, space_id: str) -> list[dict[str, Any]]:
        url = f"{self._project_url(space_id)}/repository/tags"
        return self._paginated_get(url)

    def get_branch(self, space_id: str, branch: str) -> dict[str, Any]:
        import httpx

        url = f"{self._project_url(space_id)}/repository/branches/{quote(branch, safe='')}"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=30)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BackupGitLabAdapterError(
                f"GitLab request failed: {exc}",
                status_code=exc.response.status_code,
            ) from exc
        return response.json()

    def get_project_url(self, space_id: str) -> str:
        return f"{self.base_url}/{self._project_path(space_id)}"


class StubBackupGitLabAdapter(BackupGitLabAdapter):
    """In-memory stub for unit tests. No external calls."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = state or {}

    def _get(self, key: tuple[Any, ...], default: Any) -> Any:
        return self.state.get(key, default)

    def list_merge_requests(self, space_id: str) -> list[dict[str, Any]]:
        return list(self._get(("mrs", space_id), []))

    def list_notes(self, space_id: str, mr_iid: int) -> list[dict[str, Any]]:
        return list(self._get(("notes", space_id, mr_iid), []))

    def list_tags(self, space_id: str) -> list[dict[str, Any]]:
        return list(self._get(("tags", space_id), []))

    def get_branch(self, space_id: str, branch: str) -> dict[str, Any]:
        branch_data = self._get(
            ("branch", space_id, branch),
            {"name": branch, "commit": {"id": ""}},
        )
        return dict(branch_data)

    def get_project_url(self, space_id: str) -> str:
        return f"http://stub.example.com/{space_id}"
