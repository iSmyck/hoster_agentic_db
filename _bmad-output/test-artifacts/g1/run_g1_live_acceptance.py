# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "fastapi",
#   "httpx",
#   "sqlalchemy",
#   "psycopg",
#   "pydantic",
#   "pydantic-settings",
#   "python-dotenv",
# ]
# ///

"""Live G1 vertical slice acceptance test against real local GitLab CE.

Flow exercised:
  1. Verify merge-only rules for the Space target branch.
  2. Create a proposal branch from main, add a single-page change.
  3. Submit ProposalRecord via GO (author != approver).
  4. Record independent human DecisionRecord (note+tag) via GO.
  5. Execute GO merge and verify merge commit parents + trailers.
  6. Negative cases: merge without decision, self-approval, re-merge rejected.
  7. Clean up the proposal branch.

Environment is read from the workspace .env file.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

# Load workspace .env so GO_GITLAB_URL, GO_GITLAB_TOKEN, GO_DATABASE_URL are set.
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# The package directory is named with a hyphen. Mirror it under the underscore alias
# so we can import it like normal Python code.
_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

importlib.import_module("git-orchestrator.app.main")
for _original in list(sys.modules):
    if _original.startswith("git-orchestrator"):
        _aliased = _original.replace("git-orchestrator", "git_orchestrator")
        sys.modules[_aliased] = sys.modules[_original]

from git_orchestrator.app.adapters.gitlab import HttpGitLabAdapter
from git_orchestrator.app.api.auth import AuthenticatedIdentity, get_current_identity
from git_orchestrator.app.core.config import settings
from git_orchestrator.app.main import create_app
from git_orchestrator.app.repositories.db import get_db

OUTPUT_DIR = Path(__file__).resolve().parent
REPORT_JSON = OUTPUT_DIR / "g1-live-results.json"
REPORT_MD = OUTPUT_DIR / "g1-live-summary.md"
EVIDENCE_DIR = Path(__file__).resolve().parents[3] / "specs" / "corporate-kb" / "evidence" / "g1"
EVIDENCE_JSON = EVIDENCE_DIR / "g1-live-results.json"
EVIDENCE_MD = EVIDENCE_DIR / "g1-live-summary.md"

SPACE_ID = "corp-kb/sales"
TARGET_BRANCH = "main"
AUTHOR_ID = "user-sales-editor"
APPROVER_ID = "user-sales-approver"


def _validate_reset_target(database_url: str, schema: str | None) -> None:
    import os
    import re

    if os.environ.get("G1_ALLOW_DESTRUCTIVE_RESET") != "1":
        raise RuntimeError("set G1_ALLOW_DESTRUCTIVE_RESET=1 for the disposable G1 schema")
    if not schema or not re.fullmatch(r"kb_ops_g1_test(_[a-z0-9_]+)?", schema):
        raise RuntimeError("GO_KB_OPS_SCHEMA must be a dedicated kb_ops_g1_test* schema")
    if make_url(database_url).host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("destructive G1 reset is allowed only on localhost")


def _safe_dsn(database_url: str) -> str:
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(database_url)
    return urlunsplit(
        (parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, parts.query, parts.fragment)
    )


def _wait_for_mergeable(adapter: HttpGitLabAdapter, mr_iid: int, timeout: float = 45.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        mr = adapter.get_merge_request(SPACE_ID, mr_iid)
        if (
            mr.get("detailed_merge_status") == "mergeable"
            or mr.get("merge_status") == "can_be_merged"
        ):
            return
        time.sleep(0.5)
    raise RuntimeError(f"MR {mr_iid} did not become mergeable within {timeout}s")


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    expected: str,
    actual: str,
    details: dict[str, Any] | None = None,
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": status,
            "expected": expected,
            "actual": actual,
            "details": details or {},
        }
    )


def _project_path(space_id: str) -> str:
    prefix = getattr(settings, "GITLAB_PROJECT_PATH_PREFIX", "")
    return f"{prefix}{space_id}"


def _gitlab_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.GITLAB_TOKEN}"}


def _gitlab_project_url(space_id: str) -> str:
    encoded = space_id.replace("/", "%2F")
    return f"{settings.GITLAB_URL}/api/v4/projects/{encoded}"


def _get_main_head() -> str:
    url = f"{_gitlab_project_url(SPACE_ID)}/repository/branches/{TARGET_BRANCH}"
    r = httpx.get(url, headers=_gitlab_headers(), timeout=30)
    r.raise_for_status()
    return str(r.json()["commit"]["id"])


def _create_branch_and_proposal_commit(base_sha: str) -> tuple[str, str]:
    """Return (proposal_sha, proposal_branch_name)."""
    run_id = uuid.uuid4().hex[:12]
    temp_branch = f"temp-g1-{run_id}"

    # 1. Create a temporary branch from the base commit.
    branch_url = f"{_gitlab_project_url(SPACE_ID)}/repository/branches"
    r = httpx.post(
        branch_url,
        headers=_gitlab_headers(),
        json={"branch": temp_branch, "ref": base_sha},
        timeout=30,
    )
    r.raise_for_status()

    # 2. Commit a single-page change to the temporary branch.
    file_path = f"docs/g1-proposal-{run_id}.md"
    content = f"# G1 proposal {run_id}\n\nLive acceptance test change.\n"
    commit_url = f"{_gitlab_project_url(SPACE_ID)}/repository/commits"
    r = httpx.post(
        commit_url,
        headers=_gitlab_headers(),
        json={
            "branch": temp_branch,
            "commit_message": f"G1 live acceptance proposal {run_id}",
            "actions": [
                {
                    "action": "create",
                    "file_path": file_path,
                    "content": content,
                }
            ],
        },
        timeout=30,
    )
    r.raise_for_status()
    proposal_sha = str(r.json()["id"])

    # 3. Create the GO-required proposal branch from the same commit.
    proposal_branch = f"proposal/{proposal_sha[:8]}"
    r = httpx.post(
        branch_url,
        headers=_gitlab_headers(),
        json={"branch": proposal_branch, "ref": proposal_sha},
        timeout=30,
    )
    r.raise_for_status()

    # 4. Delete the temporary branch.
    httpx.delete(
        f"{branch_url}/{temp_branch}",
        headers=_gitlab_headers(),
        timeout=30,
    )

    return proposal_sha, proposal_branch, file_path


def _create_revert_proposal_commit(base_sha: str, file_path: str) -> tuple[str, str]:
    """Return (proposal_sha, proposal_branch_name) for a revert/delete of file_path."""
    run_id = uuid.uuid4().hex[:12]
    temp_branch = f"temp-g1-revert-{run_id}"

    branch_url = f"{_gitlab_project_url(SPACE_ID)}/repository/branches"
    r = httpx.post(
        branch_url,
        headers=_gitlab_headers(),
        json={"branch": temp_branch, "ref": base_sha},
        timeout=30,
    )
    r.raise_for_status()

    commit_url = f"{_gitlab_project_url(SPACE_ID)}/repository/commits"
    r = httpx.post(
        commit_url,
        headers=_gitlab_headers(),
        json={
            "branch": temp_branch,
            "commit_message": f"G1 live acceptance revert {run_id}",
            "actions": [{"action": "delete", "file_path": file_path}],
        },
        timeout=30,
    )
    r.raise_for_status()
    proposal_sha = str(r.json()["id"])

    proposal_branch = f"proposal/{proposal_sha[:8]}"
    r = httpx.post(
        branch_url,
        headers=_gitlab_headers(),
        json={"branch": proposal_branch, "ref": proposal_sha},
        timeout=30,
    )
    r.raise_for_status()

    httpx.delete(
        f"{branch_url}/{temp_branch}",
        headers=_gitlab_headers(),
        timeout=30,
    )

    return proposal_sha, proposal_branch


def _file_exists_at_sha(file_path: str, sha: str) -> bool:
    url = f"{_gitlab_project_url(SPACE_ID)}/repository/files/{file_path.replace('/', '%2F')}/raw"
    r = httpx.get(url, headers=_gitlab_headers(), params={"ref": sha}, timeout=30)
    return r.status_code == 200


def _delete_branch(branch: str) -> None:
    branch_url = f"{_gitlab_project_url(SPACE_ID)}/repository/branches"
    httpx.delete(
        f"{branch_url}/{branch}",
        headers=_gitlab_headers(),
        timeout=30,
    )


def _verify_merge_commit(
    merge_sha: str, expected_base: str, expected_proposal: str
) -> dict[str, Any]:
    url = f"{_gitlab_project_url(SPACE_ID)}/repository/commits/{merge_sha}"
    r = httpx.get(url, headers=_gitlab_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    parents = data.get("parent_ids", [])
    trailers = data.get("trailers", {})
    return {
        "parents": parents,
        "first_parent_matches_base": parents[0] == expected_base if parents else False,
        "second_parent_matches_proposal": parents[1] == expected_proposal
        if len(parents) >= 2
        else False,
        "trailers": trailers,
        "message": data.get("message", ""),
    }


def _verify_decision_tag(decision_id: str, expected_proposal_sha: str) -> dict[str, Any]:
    tag_name = f"kb-decisions/{decision_id}"
    url = f"{_gitlab_project_url(SPACE_ID)}/repository/tags/{tag_name.replace('/', '%2F')}"
    r = httpx.get(url, headers=_gitlab_headers(), timeout=30)
    if r.status_code == 404:
        return {"found": False}
    r.raise_for_status()
    data = r.json()

    # Also verify the tag is protected (ADR-013 / G1 requirement).
    protected_url = f"{_gitlab_project_url(SPACE_ID)}/protected_tags/{tag_name.replace('/', '%2F')}"
    pr = httpx.get(protected_url, headers=_gitlab_headers(), timeout=30)
    protected = pr.status_code == 200

    return {
        "found": True,
        "target": data.get("commit", {}).get("id"),
        "target_matches_proposal_sha": data.get("commit", {}).get("id") == expected_proposal_sha,
        "protected": protected,
        "message": data.get("message", ""),
    }


def _run_negative_cases(
    client: TestClient,
    proposal_base: dict[str, Any],
    cleanup_branches: list[str],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    # A missing source branch is a separate submit-time rejection.
    missing = client.post(
        "/api/kb/v1/proposals",
        json={
            **proposal_base,
            "proposal_sha": "0" * 40,
            "base_sha": "0" * 40,
            "idempotency_key": f"g1-missing-{uuid.uuid4().hex[:8]}",
        },
    )
    _check(
        checks,
        "negative.source_branch_not_found",
        "PASS" if missing.status_code == 404 else "FAIL",
        "proposal without source branch is rejected before merge",
        f"status={missing.status_code}",
    )

    # A valid proposal without a decision must reach the merge guard.
    orphan_sha, orphan_branch, _ = _create_branch_and_proposal_commit(proposal_base["base_sha"])
    cleanup_branches.append(orphan_branch)
    orphan = client.post(
        "/api/kb/v1/proposals",
        json={
            **proposal_base,
            "proposal_sha": orphan_sha,
            "idempotency_key": f"g1-orphan-{uuid.uuid4().hex[:8]}",
        },
    )
    if orphan.status_code != 201:
        _check(
            checks,
            "negative.merge_without_decision",
            "FAIL",
            "valid proposal without decision is created",
            f"status={orphan.status_code}, body={orphan.text}",
        )
    else:
        orphan_id = orphan.json()["id"]
        r = client.post(f"/api/kb/v1/proposals/{orphan_id}/merge")
        _check(
            checks,
            "negative.merge_without_decision",
            "PASS"
            if r.status_code == 409 and r.json().get("detail", {}).get("code") == "INVALID_STATE"
            else "FAIL",
            "merge without decision rejected with INVALID_STATE",
            f"status={r.status_code}, code={r.json().get('detail', {}).get('code')}",
            {"status_code": r.status_code, "response": r.json()},
        )

    # Spoofing another actor is rejected before decision anchors are created.
    self_sha, self_branch, _ = _create_branch_and_proposal_commit(proposal_base["base_sha"])
    cleanup_branches.append(self_branch)
    self_prop = client.post(
        "/api/kb/v1/proposals",
        json={
            **proposal_base,
            "proposal_sha": self_sha,
            "idempotency_key": f"g1-self-{uuid.uuid4().hex[:8]}",
        },
    )
    self_id = self_prop.json()["id"]
    spoof = client.post(
        "/api/kb/v1/decisions",
        json={
            "proposal_id": self_id,
            "action": "accepted",
            "actor_id": AUTHOR_ID,
            "idempotency_key": f"g1-self-decision-{uuid.uuid4().hex[:8]}",
        },
    )
    _check(
        checks,
        "negative.actor_spoofing_rejected",
        "PASS"
        if spoof.status_code == 403
        and spoof.json().get("detail", {}).get("code") == "ACTOR_MISMATCH"
        else "FAIL",
        "actor spoofing rejected before DecisionRecord anchors",
        f"status={spoof.status_code}, code={spoof.json().get('detail', {}).get('code')}",
    )

    # A real self-approval session is also rejected before anchors.
    client.app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity(
        stable_id=AUTHOR_ID,
        role="admin",
    )
    self_decision = client.post(
        "/api/kb/v1/decisions",
        json={
            "proposal_id": self_id,
            "action": "accepted",
            "actor_id": AUTHOR_ID,
            "idempotency_key": f"g1-real-self-decision-{uuid.uuid4().hex[:8]}",
        },
    )
    _check(
        checks,
        "negative.self_approval_by_author",
        "PASS"
        if self_decision.status_code == 403
        and self_decision.json().get("detail", {}).get("code") == "SELF_APPROVAL"
        else "FAIL",
        "self-approval rejected before DecisionRecord anchors",
        f"status={self_decision.status_code}, code={self_decision.json().get('detail', {}).get('code')}",
    )

    def _restore_identity(request: Request) -> AuthenticatedIdentity:
        if request.url.path.endswith("/decisions") or request.url.path.endswith("/merge"):
            return AuthenticatedIdentity(stable_id=APPROVER_ID, role="admin")
        return AuthenticatedIdentity(stable_id=AUTHOR_ID, role="user")

    client.app.dependency_overrides[get_current_identity] = _restore_identity
    return checks


def main() -> int:
    checks: list[dict[str, Any]] = []
    cleanup_branches: list[str] = []
    generated_at = datetime.now(UTC).isoformat()

    # Real adapter + real PostgreSQL.
    adapter = HttpGitLabAdapter(
        settings.GITLAB_URL,
        settings.GITLAB_TOKEN,
        getattr(settings, "GITLAB_PROJECT_PATH_PREFIX", ""),
    )
    engine = create_engine(settings.DATABASE_URL)
    # Reset the operational schema and run the real GO migrations so the test
    # reflects actual deployment and starts from a clean state.
    schema = settings.KB_OPS_SCHEMA
    _validate_reset_target(settings.DATABASE_URL, schema)
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

    alembic_ini = _SRC / "git-orchestrator" / "migrations" / "alembic.ini"
    migration_env = os.environ.copy()
    migration_env["GO_KB_OPS_SCHEMA"] = schema
    migration_env["DATABASE_URL"] = settings.DATABASE_URL
    subprocess.run(
        ["uv", "run", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
        check=True,
        cwd=Path(__file__).resolve().parents[3],
        env=migration_env,
    )
    SessionLocal = sessionmaker(bind=engine)

    def _get_db_session() -> Session:
        return SessionLocal()

    app = create_app(adapter=adapter)

    def _override_identity(request: Request) -> AuthenticatedIdentity:
        if request.url.path.endswith("/decisions") or request.url.path.endswith("/merge"):
            return AuthenticatedIdentity(stable_id=APPROVER_ID, role="admin")
        return AuthenticatedIdentity(stable_id=AUTHOR_ID, role="user")

    app.dependency_overrides[get_current_identity] = _override_identity

    async def _override_get_db():
        session = _get_db_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    try:
        # Precondition: health.
        r = client.get("/health")
        _check(
            checks,
            "precondition.health",
            "PASS" if r.status_code == 200 else "FAIL",
            "GO health endpoint returns 200",
            f"status={r.status_code}, body={r.json()}",
        )

        # Precondition: merge-only rules via GO HTTP route.
        r = client.get(f"/api/kb/v1/spaces/{SPACE_ID}/merge-rules")
        if r.status_code == 200:
            rules = r.json()
            _check(
                checks,
                "precondition.merge_only_rules",
                "PASS" if rules.get("protected") and rules.get("merge_only") else "FAIL",
                "target branch is protected and merge-only",
                f"protected={rules.get('protected')}, merge_only={rules.get('merge_only')}",
                rules,
            )
        else:
            _check(
                checks,
                "precondition.merge_only_rules",
                "FAIL",
                "target branch is protected and merge-only",
                f"status={r.status_code}, body={r.text}",
            )

        # G1 happy path.
        base_sha = _get_main_head()
        proposal_sha, proposal_branch, file_path = _create_branch_and_proposal_commit(base_sha)
        cleanup_branches.append(proposal_branch)

        proposal_base = {
            "space_id": SPACE_ID,
            "proposal_sha": proposal_sha,
            "base_sha": base_sha,
            "target_branch": TARGET_BRANCH,
            "idempotency_key": f"g1-acceptance-{uuid.uuid4().hex[:8]}",
            "proposal_data": {
                "author_stable_id": AUTHOR_ID,
                "requester_stable_id": AUTHOR_ID,
                "target_branch": TARGET_BRANCH,
            },
        }

        # 1. Submit proposal.
        r = client.post("/api/kb/v1/proposals", json=proposal_base)
        _check(
            checks,
            "flow.submit_proposal",
            "PASS" if r.status_code == 201 else "FAIL",
            "proposal accepted and MR created",
            f"status={r.status_code}, body={r.json() if r.status_code == 201 else r.text}",
        )
        proposal_id = r.json()["id"]
        mr_iid = r.json()["proposal_data"]["mr_iid"]

        # 2. Record independent decision.
        decision_key = f"g1-decision-{uuid.uuid4().hex[:8]}"
        r = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": APPROVER_ID,
                "idempotency_key": decision_key,
                "decision_data": {
                    "policy_bundle_id": "sales-policy-bundle",
                    "access_policy_revision": "a" * 40,
                    "approval_policy_revision": "b" * 40,
                },
            },
        )
        _check(
            checks,
            "flow.record_decision",
            "PASS" if r.status_code == 201 else "FAIL",
            "independent human decision recorded with note+tag",
            f"status={r.status_code}, body={r.json() if r.status_code == 201 else r.text}",
        )
        decision_id = r.json()["id"]

        # 3. Execute merge after GitLab reports the MR mergeable.
        _wait_for_mergeable(adapter, mr_iid)
        r = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        _check(
            checks,
            "flow.execute_merge",
            "PASS" if r.status_code == 200 else "FAIL",
            "GO merge succeeds and returns merge_sha",
            f"status={r.status_code}, body={r.json() if r.status_code == 200 else r.text}",
        )

        merge_sha: str | None = None
        if r.status_code == 200:
            merge_sha = r.json()["merge_sha"]
            merge_proof = _verify_merge_commit(merge_sha, base_sha, proposal_sha)
            _check(
                checks,
                "flow.merge_parentage",
                "PASS"
                if merge_proof["first_parent_matches_base"]
                and merge_proof["second_parent_matches_proposal"]
                else "FAIL",
                "merge commit parents equal base_sha and proposal_sha",
                f"parents={merge_proof['parents']}",
                merge_proof,
            )
            _check(
                checks,
                "flow.merge_trailers",
                "PASS" if str(decision_id) in merge_proof["message"] else "FAIL",
                "merge commit message contains Decision-ID trailer",
                merge_proof["message"],
                merge_proof,
            )

        # 4. Verify protected decision tag.
        tag_proof = _verify_decision_tag(decision_id, proposal_sha)
        _check(
            checks,
            "flow.decision_tag",
            "PASS"
            if tag_proof.get("found")
            and tag_proof.get("target_matches_proposal_sha")
            and tag_proof.get("protected")
            else "FAIL",
            "protected annotated tag exists on proposal_sha",
            f"found={tag_proof.get('found')}, target_matches={tag_proof.get('target_matches_proposal_sha')}, protected={tag_proof.get('protected')}",
            tag_proof,
        )

        # 5. Negative cases.
        checks.extend(_run_negative_cases(client, proposal_base, cleanup_branches))

        # 6. Identical merge replay returns the existing Git-derived result.
        r = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        _check(
            checks,
            "flow.merge_replay_idempotent",
            "PASS" if r.status_code == 200 and r.json().get("merge_sha") == merge_sha else "FAIL",
            "merge replay returns existing merge_sha without another external merge",
            f"status={r.status_code}, merge_sha={r.json().get('merge_sha')}",
            {"status_code": r.status_code, "response": r.json()},
        )

        # 7. Revert / restore flow: create a new proposal that deletes the merged file.
        revert_base_sha = _get_main_head()
        revert_proposal_sha, revert_proposal_branch = _create_revert_proposal_commit(
            revert_base_sha, file_path
        )
        cleanup_branches.append(revert_proposal_branch)

        revert_base = {
            "space_id": SPACE_ID,
            "proposal_sha": revert_proposal_sha,
            "base_sha": revert_base_sha,
            "target_branch": TARGET_BRANCH,
            "idempotency_key": f"g1-revert-{uuid.uuid4().hex[:8]}",
            "proposal_data": {
                "author_stable_id": AUTHOR_ID,
                "requester_stable_id": AUTHOR_ID,
                "target_branch": TARGET_BRANCH,
                "reverts_decision_id": decision_id,
            },
        }

        r = client.post("/api/kb/v1/proposals", json=revert_base)
        _check(
            checks,
            "flow.revert.submit_proposal",
            "PASS" if r.status_code == 201 else "FAIL",
            "revert proposal accepted and MR created",
            f"status={r.status_code}, body={r.json() if r.status_code == 201 else r.text}",
        )
        revert_proposal_id = r.json()["id"] if r.status_code == 201 else None
        revert_mr_iid = r.json()["proposal_data"]["mr_iid"] if r.status_code == 201 else None

        revert_decision_id: str | None = None
        if revert_proposal_id:
            r = client.post(
                "/api/kb/v1/decisions",
                json={
                    "proposal_id": revert_proposal_id,
                    "action": "accepted",
                    "actor_id": APPROVER_ID,
                    "idempotency_key": f"g1-revert-decision-{uuid.uuid4().hex[:8]}",
                    "decision_data": {
                        "policy_bundle_id": "sales-policy-bundle",
                        "access_policy_revision": "a" * 40,
                        "approval_policy_revision": "b" * 40,
                        "reverts_decision_id": decision_id,
                    },
                },
            )
            _check(
                checks,
                "flow.revert.record_decision",
                "PASS" if r.status_code == 201 else "FAIL",
                "revert decision recorded with note+tag",
                f"status={r.status_code}, body={r.json() if r.status_code == 201 else r.text}",
            )
            if r.status_code == 201:
                revert_decision_id = r.json()["id"]

        if revert_proposal_id and revert_mr_iid:
            _wait_for_mergeable(adapter, revert_mr_iid)
            r = client.post(f"/api/kb/v1/proposals/{revert_proposal_id}/merge")
            _check(
                checks,
                "flow.revert.execute_merge",
                "PASS" if r.status_code == 200 else "FAIL",
                "revert merge succeeds and returns merge_sha",
                f"status={r.status_code}, body={r.json() if r.status_code == 200 else r.text}",
            )

            if r.status_code == 200:
                revert_merge_sha = r.json()["merge_sha"]
                revert_proof = _verify_merge_commit(
                    revert_merge_sha, revert_base_sha, revert_proposal_sha
                )
                _check(
                    checks,
                    "flow.revert.merge_parentage",
                    "PASS"
                    if revert_proof["first_parent_matches_base"]
                    and revert_proof["second_parent_matches_proposal"]
                    else "FAIL",
                    "revert merge commit parents equal revert base_sha and proposal_sha",
                    f"parents={revert_proof['parents']}",
                    revert_proof,
                )
                _check(
                    checks,
                    "flow.revert.merge_trailers",
                    "PASS" if str(revert_decision_id) in revert_proof["message"] else "FAIL",
                    "revert merge commit message contains Decision-ID trailer",
                    revert_proof["message"],
                    revert_proof,
                )

                # Verify the file was deleted/restored (does not exist at main HEAD).
                restored = not _file_exists_at_sha(file_path, revert_merge_sha)
                _check(
                    checks,
                    "flow.revert.file_restored",
                    "PASS" if restored else "FAIL",
                    "merged file no longer exists after revert merge",
                    f"file_path={file_path}, exists={not restored}",
                )

                if revert_decision_id:
                    tag_proof = _verify_decision_tag(revert_decision_id, revert_proposal_sha)
                    _check(
                        checks,
                        "flow.revert.decision_tag",
                        "PASS"
                        if tag_proof.get("found")
                        and tag_proof.get("target_matches_proposal_sha")
                        and tag_proof.get("protected")
                        else "FAIL",
                        "protected annotated tag exists on revert proposal_sha",
                        f"found={tag_proof.get('found')}, target_matches={tag_proof.get('target_matches_proposal_sha')}, protected={tag_proof.get('protected')}",
                        tag_proof,
                    )

    except Exception as exc:  # noqa: BLE001
        _check(
            checks,
            "harness.exception",
            "FAIL",
            "no unexpected exception",
            f"{type(exc).__name__}: {exc}",
        )

    finally:
        for branch in cleanup_branches:
            try:
                _delete_branch(branch)
            except Exception as exc:  # noqa: BLE001
                checks.append(
                    {
                        "id": f"cleanup.delete_branch.{branch}",
                        "status": "FAIL",
                        "expected": "proposal branch deleted",
                        "actual": f"{type(exc).__name__}: {exc}",
                    }
                )

        with contextlib.suppress(Exception):
            engine.dispose()

    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    blocked_count = sum(1 for c in checks if c["status"] == "BLOCKED")

    report = {
        "schema_version": "g1-live-acceptance-v1",
        "generated_at": generated_at,
        "environment": {
            "sandbox": "live_local_gitlab_ce",
            "gitlab_url": settings.GITLAB_URL,
            "gitlab_project": _project_path(SPACE_ID),
            "database": _safe_dsn(settings.DATABASE_URL),
            "pinned_toolchain": {
                "open_webui": "v0.13.0",
                "open_webui_commit": "c38885a1a737da4968f157092f304f3b5481d0bf",
                "python": "3.12.13",
                "uv": "0.11.13",
            },
        },
        "sensitive_data_included": False,
        "command": "uv run python _bmad-output/test-artifacts/g1/run_g1_live_acceptance.py",
        "counts": {
            "PASS": pass_count,
            "FAIL": fail_count,
            "BLOCKED": blocked_count,
            "TOTAL": len(checks),
        },
        "checks": checks,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    REPORT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    EVIDENCE_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )

    md = _render_markdown(report)
    REPORT_MD.write_text(md, encoding="utf-8")
    EVIDENCE_MD.write_text(md, encoding="utf-8")

    print(f"Wrote {REPORT_JSON}")
    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {EVIDENCE_JSON}")
    print(f"Wrote {EVIDENCE_MD}")
    print(f"Counts: {report['counts']}")

    return 1 if fail_count > 0 else 0


def _render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "# G1 Live Vertical Slice Acceptance Evidence",
        "",
        f"- **Generated:** {report['generated_at']}",
        f"- **Environment:** {report['environment']['sandbox']}",
        f"- **GitLab:** {report['environment']['gitlab_url']} / {report['environment']['gitlab_project']}",
        "",
        "## Counts",
        "",
        f"- PASS: {counts['PASS']}",
        f"- FAIL: {counts['FAIL']}",
        f"- BLOCKED: {counts['BLOCKED']}",
        f"- TOTAL: {counts['TOTAL']}",
        "",
        "## Checks",
        "",
        "| ID | Status | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for c in report["checks"]:
        actual_short = (c["actual"] or "")[:120].replace("|", "\\|")
        lines.append(f"| {c['id']} | {c['status']} | {c['expected']} | {actual_short} |")
    lines.append("")
    lines.append("## Rerun instructions")
    lines.append("")
    lines.append(f"```bash\n{report['command']}\n```")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
