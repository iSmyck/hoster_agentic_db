#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx",
# ]
# ///

"""Create a KB document draft (and optionally a proposal) through the Git Orchestrator API.

This is a local-dev helper for the G1 canonical write path:

    Session token -> GO draft -> GO proposal -> (review -> merge)

Open WebUI Knowledge is a read/test projection, not the canonical source.
New documents must enter the Git-native lifecycle via GO.

Examples:
    uv run python scripts/create_kb_document.py docs/runbook.md --title "Runbook"
    uv run python scripts/create_kb_document.py docs/runbook.md --title "Runbook" --propose
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

SESSION_URL = os.environ.get("SESSION_SERVICE_URL", "http://127.0.0.1:8004")
GO_URL = os.environ.get("GO_SERVICE_URL", "http://127.0.0.1:8002")
DEFAULT_SPACE = os.environ.get("KB_SPACE_ID", "corp-kb/sales")
DEFAULT_BRANCH = os.environ.get("KB_TARGET_BRANCH", "main")
DEFAULT_AUTHOR = os.environ.get("KB_AUTHOR_ID", "author-1")


def _create_session(author_id: str) -> str:
    r = httpx.post(
        f"{SESSION_URL}/api/kb/v1/session/create",
        json={"stable_id": author_id},
        timeout=10,
    )
    r.raise_for_status()
    return str(r.json()["access_token"])


def _save_draft(
    token: str,
    space_id: str,
    path: str,
    branch: str,
    content: str,
) -> dict:
    r = httpx.post(
        f"{GO_URL}/api/kb/v1/drafts/save",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "space_id": space_id,
            "path": path,
            "target_branch": branch,
            "content": content,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def _prepare_branch(
    token: str,
    space_id: str,
    path: str,
    branch: str,
    content: str,
    idempotency_key: str,
) -> dict:
    r = httpx.post(
        f"{GO_URL}/api/g1-editor/prepare-branch",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "space_id": space_id,
            "branch": branch,
            "file_path": path,
            "content": content,
            "idempotency_key": idempotency_key,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def _submit_proposal(
    token: str,
    space_id: str,
    path: str,
    branch: str,
    title: str,
    content: str,
    proposal_sha: str,
    base_sha: str,
    idempotency_key: str,
) -> dict:
    r = httpx.post(
        f"{GO_URL}/api/kb/v1/proposals",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "space_id": space_id,
            "proposal_sha": proposal_sha,
            "base_sha": base_sha,
            "target_branch": branch,
            "idempotency_key": idempotency_key,
            "proposal_data": {
                "title": title,
                "description": f"Proposal for {path}",
                "files": [
                    {
                        "path": path,
                        "content": content,
                        "operation": "create",
                    }
                ],
            },
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a KB document draft via GO")
    parser.add_argument("path", help="Markdown path under the Space, e.g. docs/runbook.md")
    parser.add_argument(
        "--content",
        "-c",
        help="Inline markdown content; if omitted, reads from stdin or a file",
    )
    parser.add_argument(
        "--file",
        "-f",
        help="Read markdown content from this file instead of stdin/inline",
    )
    parser.add_argument(
        "--space",
        "-s",
        default=DEFAULT_SPACE,
        help=f"Space (GitLab project path), default: {DEFAULT_SPACE}",
    )
    parser.add_argument(
        "--branch",
        "-b",
        default=DEFAULT_BRANCH,
        help=f"Target branch, default: {DEFAULT_BRANCH}",
    )
    parser.add_argument(
        "--author",
        "-a",
        default=DEFAULT_AUTHOR,
        help=f"Author stable_id for session service, default: {DEFAULT_AUTHOR}",
    )
    parser.add_argument(
        "--title",
        "-t",
        default=None,
        help="Proposal title (used with --propose)",
    )
    parser.add_argument(
        "--propose",
        action="store_true",
        help="Also submit a proposal/MR for the new document",
    )
    args = parser.parse_args()

    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    elif args.content:
        content = args.content
    else:
        content = sys.stdin.read()

    if not content.strip():
        print("Error: content is empty.", file=sys.stderr)
        return 1

    title = args.title or f"Add {args.path}"

    print(f"Creating session for {args.author}...")
    token = _create_session(args.author)

    print(f"Saving draft {args.path} in {args.space}...")
    draft = _save_draft(token, args.space, args.path, args.branch, content)
    print(f"  draft id: {draft.get('id')}")
    print(f"  space:    {draft.get('space_id')}")
    print(f"  path:     {draft.get('path')}")
    print(f"  updated:  {draft.get('updated_at')}")

    if args.propose:
        import uuid

        idempotency_key = str(uuid.uuid4())
        print("Preparing proposal branch...")
        try:
            prepared = _prepare_branch(
                token, args.space, args.path, args.branch, content, idempotency_key
            )
        except httpx.HTTPStatusError as exc:
            print(
                f"  prepare-branch failed ({exc.response.status_code}): {exc.response.text[:200]}",
                file=sys.stderr,
            )
            print(
                "  Hint: with GO_GITLAB_ADAPTER=stub the full proposal/MR path needs a live GitLab project.",
                file=sys.stderr,
            )
            return 0
        print(f"  proposal sha: {prepared.get('proposal_sha')}")
        print(f"  base sha:     {prepared.get('base_sha')}")
        print(f"  branch:       {prepared.get('proposal_branch')}")

        print("Submitting proposal...")
        proposal = _submit_proposal(
            token,
            args.space,
            args.path,
            args.branch,
            title,
            content,
            prepared["proposal_sha"],
            prepared["base_sha"],
            idempotency_key,
        )
        print(f"  proposal id: {proposal.get('id')}")
        print(f"  status:      {proposal.get('status')}")
        print(f"  branch:      proposal/{proposal.get('proposal_sha', '')[:8]}")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
