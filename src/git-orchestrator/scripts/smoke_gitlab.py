#!/usr/bin/env python3
"""Smoke test Git Orchestrator adapter against real local GitLab CE."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import httpx

_SRC = Path(__file__).resolve().parents[2]  # src/git-orchestrator/scripts -> src
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

importlib.import_module("git-orchestrator.app.main")
for _original in list(sys.modules):
    if _original.startswith("git-orchestrator"):
        _aliased = _original.replace("git-orchestrator", "git_orchestrator")
        sys.modules[_aliased] = sys.modules[_original]

from git_orchestrator.app.adapters.gitlab import HttpGitLabAdapter
from git_orchestrator.app.core.config import settings


def _current_head(space_id: str) -> str:
    """Fetch current HEAD SHA via GitLab commits API using numeric project id."""
    # Use numeric project id to avoid path encoding issues in this quick smoke test.
    url = f"{settings.GITLAB_URL}/api/v4/projects/1/repository/commits/main"
    response = httpx.get(url, headers={"Authorization": f"Bearer {settings.GITLAB_TOKEN}"}, timeout=10)
    response.raise_for_status()
    return response.json()["id"]


def main() -> int:
    adapter = HttpGitLabAdapter(
        base_url=settings.GITLAB_URL,
        token=settings.GITLAB_TOKEN,
        project_path_prefix=settings.GITLAB_PROJECT_PATH_PREFIX,
    )
    space_id = "corp-kb/sales"
    print(f"Testing GitLab adapter at {settings.GITLAB_URL} for {space_id}")

    head = _current_head(space_id)
    print(f"HEAD: {head}")

    tree = adapter.get_tree(space_id, head)
    print(f"Tree entries: {len(tree)}")
    for entry in tree[:5]:
        print(f"  - {entry['path']} ({entry['type']})")

    if tree:
        first_file = next((e for e in tree if e["type"] == "blob"), None)
        if first_file:
            content = adapter.read_document(space_id, first_file["path"], head)
            print(f"First file ({first_file['path']}) length: {len(content)} bytes")

    rules = adapter.protected_branch_rules(space_id)
    print(f"Protected branch rules: {rules}")

    exists = adapter.branch_exists(space_id, "main")
    print(f"Branch main exists: {exists}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
