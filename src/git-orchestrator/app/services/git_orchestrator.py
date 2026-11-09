"""Git Orchestrator business logic."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..adapters.gitlab import GitLabAdapter, GitLabAdapterError
from ..models.ops import DecisionRecord, ProposalRecord
from ..schemas.ops import DecisionRecordRequest, ProposalSubmitRequest


class GitOrchestratorError(Exception):
    """Domain error raised by the Git Orchestrator."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def read_document(
    db: Session,
    adapter: GitLabAdapter,
    space_id: str,
    path: str,
    sha: str,
) -> str:
    """Exact-SHA read of ``path`` from GitLab."""
    return adapter.read_document(space_id, path, sha)


def get_tree(
    db: Session,
    adapter: GitLabAdapter,
    space_id: str,
    sha: str,
) -> list[dict[str, Any]]:
    """Return the tree for ``space_id`` at ``sha``."""
    return adapter.get_tree(space_id, sha)


def submit_proposal(
    db: Session,
    adapter: GitLabAdapter,
    request: ProposalSubmitRequest,
) -> ProposalRecord:
    """Create a ProposalRecord projection and an MR in GitLab."""
    existing = (
        db.query(ProposalRecord)
        .filter_by(
            space_id=request.space_id,
            idempotency_key=request.idempotency_key,
        )
        .first()
    )
    if existing is not None:
        if existing.proposal_sha != request.proposal_sha:
            raise GitOrchestratorError(
                "IDEMPOTENCY_KEY_REUSED",
                "idempotency_key already used with a different proposal_sha",
            )
        return existing

    source_branch = f"proposal/{request.proposal_sha[:8]}"
    if not adapter.branch_exists(request.space_id, source_branch):
        raise GitOrchestratorError(
            "SOURCE_BRANCH_NOT_FOUND",
            f"source branch {source_branch} does not exist",
        )

    proposal_data = {
        **request.proposal_data,
        "target_branch": request.target_branch,
    }

    record = ProposalRecord(
        space_id=request.space_id,
        proposal_sha=request.proposal_sha,
        base_sha=request.base_sha,
        target_sha=request.target_sha,
        proposal_data=proposal_data,
        status="in_review",
        idempotency_key=request.idempotency_key,
    )
    db.add(record)
    db.flush()

    try:
        mr = adapter.create_merge_request(
            request.space_id,
            source_branch,
            request.target_branch,
            f"Proposal {request.proposal_sha[:8]}",
        )
    except (GitLabAdapterError, httpx.HTTPError) as exc:
        db.rollback()
        raise GitOrchestratorError(
            "MR_CREATE_FAILED",
            f"failed to create merge request: {exc}",
        ) from exc

    record.proposal_data = {**record.proposal_data, "mr_iid": mr.get("iid")}
    db.flush()
    return record


def record_decision(
    db: Session,
    adapter: GitLabAdapter,
    request: DecisionRecordRequest,
) -> DecisionRecord:
    """Record a human decision for a proposal."""
    existing = (
        db.query(DecisionRecord)
        .filter_by(idempotency_key=request.idempotency_key)
        .first()
    )
    if existing is not None:
        if existing.proposal_id != request.proposal_id or existing.outcome != request.action:
            raise GitOrchestratorError(
                "IDEMPOTENCY_KEY_REUSED",
                "idempotency_key already used with a different decision",
            )
        return existing

    proposal = db.get(ProposalRecord, request.proposal_id)
    if proposal is None:
        raise GitOrchestratorError("NOT_FOUND", "proposal not found")
    if proposal.status in ("rejected", "cancelled", "merged"):
        raise GitOrchestratorError(
            "INVALID_STATE",
            f"proposal is already {proposal.status}",
        )

    record = DecisionRecord(
        proposal_id=proposal.id,
        outcome=request.action,
        decision_data=request.decision_data,
        actor_id=request.actor_id,
        idempotency_key=request.idempotency_key,
    )
    db.add(record)

    if request.action in ("rejected", "cancelled"):
        proposal.status = request.action

    db.flush()
    return record


def execute_merge(
    db: Session,
    adapter: GitLabAdapter,
    proposal_id: uuid.UUID,
) -> dict[str, Any]:
    """Execute a reviewed, accepted proposal merge."""
    proposal = db.get(ProposalRecord, proposal_id)
    if proposal is None:
        raise GitOrchestratorError("NOT_FOUND", "proposal not found")
    if proposal.status != "in_review":
        raise GitOrchestratorError(
            "INVALID_STATE",
            f"proposal is already {proposal.status}",
        )

    decision = (
        db.query(DecisionRecord)
        .filter_by(proposal_id=proposal.id, outcome="accepted")
        .first()
    )
    if decision is None:
        raise GitOrchestratorError(
            "INVALID_STATE",
            "no accepted decision for this proposal",
        )

    author = proposal.proposal_data.get("author_stable_id")
    requester = proposal.proposal_data.get("requester_stable_id")
    if decision.actor_id in {author, requester}:
        raise GitOrchestratorError(
            "SELF_APPROVAL",
            "approver must differ from proposal author/requester",
        )

    mr_iid = proposal.proposal_data.get("mr_iid")
    if mr_iid is not None:
        mr = adapter.get_merge_request(proposal.space_id, mr_iid)
        if mr.get("base_sha") and mr.get("base_sha") != proposal.base_sha:
            raise GitOrchestratorError(
                "BASE_MISMATCH",
                "target HEAD does not match proposal base_sha",
            )

    try:
        result = adapter.merge_merge_request(
            proposal.space_id,
            mr_iid or 1,
            proposal.proposal_sha,
        )
    except (GitLabAdapterError, httpx.HTTPError) as exc:
        raise GitOrchestratorError(
            "MERGE_FAILED",
            f"GitLab merge call failed: {exc}",
        ) from exc

    proposal.status = "merged"
    db.flush()

    return {
        "proposal_id": proposal.id,
        "status": "merged",
        "merge_sha": result.get("sha"),
        "detail": "merged via GitLab",
    }


def direct_push_guard(
    db: Session,
    adapter: GitLabAdapter,
    space_id: str,
) -> dict[str, Any]:
    """Verify that the Space target branch is merge-only."""
    rules = adapter.protected_branch_rules(space_id)
    if not (rules.get("protected") and rules.get("merge_only")):
        raise GitOrchestratorError(
            "DIRECT_PUSH_BLOCKED",
            "direct push is not permitted for this Space target branch",
        )
    return {
        "space_id": space_id,
        "protected": bool(rules.get("protected", False)),
        "merge_only": bool(rules.get("merge_only", False)),
        "rules": rules,
    }
