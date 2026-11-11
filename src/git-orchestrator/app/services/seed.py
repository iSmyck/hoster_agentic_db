"""Default synthetic seed data for G1 vertical slice tests.

This module is intended for disposable test schemas only. It must not be
wired into production endpoints or used outside explicitly allowed test
contexts.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..adapters.gitlab import StubGitLabAdapter
from . import drafts as draft_service

DEFAULT_SPACE_ID = "corp-kb/sales"
DEFAULT_TARGET_BRANCH = "main"


def seed_stub_history(adapter: StubGitLabAdapter, space_id: str = DEFAULT_SPACE_ID) -> None:
    """Populate the stub GitLab adapter with synthetic commit history."""
    history_key = ("history", space_id, "docs/g1-proposal.md", DEFAULT_TARGET_BRANCH)
    if adapter.state.get(history_key):
        return
    adapter.state[history_key] = [
        {
            "id": "a" * 40,
            "message": "Initial pricing playbook\n\nCo-authored-by: author-1",
            "author_name": "G1 Author",
            "author_email": "author-1@hoster.test",
            "committed_date": "2026-11-08T10:00:00Z",
        },
        {
            "id": "b" * 40,
            "message": "Add discount section",
            "author_name": "G1 Author",
            "author_email": "author-1@hoster.test",
            "committed_date": "2026-11-08T11:00:00Z",
        },
        {
            "id": "c" * 40,
            "message": "Update terms",
            "author_name": "G1 Approver",
            "author_email": "approver-1@hoster.test",
            "committed_date": "2026-11-08T12:00:00Z",
        },
    ]


def seed_sample_drafts(
    db: Session,
    adapter: StubGitLabAdapter,
    space_id: str = DEFAULT_SPACE_ID,
) -> list[dict[str, Any]]:
    """Create default synthetic drafts and stub history for the G1 Space.

    Returns the serialized drafts for test assertions.
    """
    seed_stub_history(adapter, space_id)

    drafts = []
    for author, path, content in (
        ("author-1", "docs/g1-proposal.md", "# G1 proposal\n\nSeeded draft content.\n"),
        ("author-1", "docs/g1-terms.md", "# Terms\n\nSeeded terms draft.\n"),
    ):
        record = draft_service.save_draft(
            db,
            space_id=space_id,
            path=path,
            author_stable_id=author,
            content=content,
            target_branch=DEFAULT_TARGET_BRANCH,
            base_sha="a" * 40,
        )
        drafts.append(draft_service.draft_to_dict(record))
    return drafts
