"""Git Orchestrator business logic."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
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


def _canonical_json(payload: dict[str, Any]) -> str:
    """Serialize a DecisionRecord to deterministic canonical JSON bytes.

    Uses compact separators and sorted keys for deterministic output.  For
    G1 vertical slice this is sufficient; RFC 8785 JCS compliance is tracked
    as a follow-up hardening item.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _record_sha256(canonical_json: str) -> str:
    """Return the SHA-256 hex digest of canonical JSON bytes."""
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _target_proposals(db: Session, space_id: str, target_branch: str) -> list[ProposalRecord]:
    """Return proposals for a target branch (Python-side filter for SQLite compat)."""
    return [
        p
        for p in db.query(ProposalRecord).filter(ProposalRecord.space_id == space_id).all()
        if p.proposal_data.get("target_branch", "main") == target_branch
    ]


def _next_fence_token(db: Session, space_id: str, target_branch: str) -> int:
    """Return the next monotonic fence token for a target."""
    proposals = _target_proposals(db, space_id, target_branch)
    return max((p.merge_fence_token for p in proposals), default=0) + 1


def _target_recovery_active(db: Session, space_id: str, target_branch: str) -> bool:
    """Return True if any proposal for this target has recovery_required set."""
    return any(p.recovery_required for p in _target_proposals(db, space_id, target_branch))


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
    """Record a human decision for a proposal with canonical note/tag anchors."""
    existing = db.query(DecisionRecord).filter_by(idempotency_key=request.idempotency_key).first()
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

    # G1 fault matrix: at most one decision per proposal unless explicitly
    # superseding the prior decision. This closes the concurrent-decision race
    # (A09) and provides a deterministic path to cancel/supersede (A28).
    prior_decision = (
        db.query(DecisionRecord).filter_by(proposal_id=proposal.id).first()
    )
    if prior_decision is not None:
        if request.supersedes_decision_id != prior_decision.id:
            raise GitOrchestratorError(
                "INVALID_STATE",
                "proposal already has a decision; use supersedes_decision_id to replace it",
            )
        if proposal.status == "merged":
            raise GitOrchestratorError(
                "INVALID_STATE",
                "cannot supersede a decision for an already-merged proposal",
            )
        prior_decision.state = "superseded"
        if proposal.status in ("rejected", "cancelled"):
            proposal.status = "in_review"
    elif request.supersedes_decision_id is not None:
        raise GitOrchestratorError(
            "NOT_FOUND", "superseded decision not found for this proposal"
        )

    if proposal.status in ("rejected", "cancelled", "merged"):
        raise GitOrchestratorError(
            "INVALID_STATE",
            f"proposal is already {proposal.status}",
        )

    principals = {
        proposal.proposal_data.get("author_stable_id"),
        proposal.proposal_data.get("requester_stable_id"),
        proposal.proposal_data.get("version_author_stable_id"),
    }
    if request.actor_id in principals:
        raise GitOrchestratorError(
            "SELF_APPROVAL",
            "approver must differ from proposal author/requester/version author",
        )

    # Derive a stable decision UUID from the idempotency key so crash+retry
    # recovers the same anchors instead of creating new ones.
    decision_id = uuid.uuid5(uuid.NAMESPACE_URL, f"kb-decision:{request.idempotency_key}")
    now = datetime.now(UTC)
    canonical = {
        "decision_id": str(decision_id),
        "proposal_id": str(proposal.id),
        "proposal_sha": proposal.proposal_sha,
        "base_sha": proposal.base_sha,
        "action": request.action,
        "actor_stable_id": request.actor_id,
        "timestamp": now.isoformat(),
        "evidence": request.decision_data.get("evidence", []),
        "policy_bundle_id": request.decision_data.get("policy_bundle_id", ""),
        "access_policy_revision": request.decision_data.get("access_policy_revision", ""),
        "approval_policy_revision": request.decision_data.get("approval_policy_revision", ""),
    }
    canonical_json = _canonical_json(canonical)
    sha256 = _record_sha256(canonical_json)
    canonical["record_sha256"] = sha256
    canonical_json = _canonical_json(canonical)
    tag_name = f"kb-decisions/{decision_id}"

    mr_iid = proposal.proposal_data.get("mr_iid")
    if mr_iid is None:
        raise GitOrchestratorError(
            "INVALID_STATE",
            "proposal has no associated merge request",
        )

    try:
        note = adapter.create_note(
            proposal.space_id,
            mr_iid,
            canonical_json,
        )
        adapter.create_tag(
            proposal.space_id,
            tag_name,
            proposal.proposal_sha,
            canonical_json,
        )
    except (GitLabAdapterError, httpx.HTTPError) as exc:
        raise GitOrchestratorError(
            "DECISION_ANCHOR_FAILED",
            f"failed to create canonical decision anchors: {exc}",
        ) from exc

    record = DecisionRecord(
        id=decision_id,
        proposal_id=proposal.id,
        outcome=request.action,
        decision_data=canonical,
        actor_id=request.actor_id,
        idempotency_key=request.idempotency_key,
        record_sha256=sha256,
        note_id=note.get("id"),
        tag_name=tag_name,
        state="recorded",
        supersedes_decision_id=request.supersedes_decision_id,
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
    actor_id: str,
) -> dict[str, Any]:
    """Execute or replay a reviewed, accepted proposal merge."""
    proposal = db.get(ProposalRecord, proposal_id)
    if proposal is None:
        raise GitOrchestratorError("NOT_FOUND", "proposal not found")

    decision = (
        db.query(DecisionRecord).filter_by(proposal_id=proposal.id, outcome="accepted").first()
    )
    if decision is not None and decision.actor_id != actor_id:
        raise GitOrchestratorError(
            "APPROVER_MISMATCH",
            "merge caller must match the accepted decision approver",
        )

    if proposal.status == "merged":
        merge_sha = proposal.target_sha
        if decision is None or not merge_sha:
            raise GitOrchestratorError(
                "INVALID_STATE", "merged proposal has no verified merge proof"
            )
        commit = adapter.get_commit(proposal.space_id, merge_sha)
        parents = commit.get("parent_ids", [])
        if (
            len(parents) < 2
            or parents[0] != proposal.base_sha
            or parents[1] != proposal.proposal_sha
        ):
            raise GitOrchestratorError(
                "MERGE_PARENT_MISMATCH",
                "stored merge proof does not match proposal parentage",
            )
        return {
            "proposal_id": str(proposal.id),
            "status": proposal.status,
            "merge_sha": merge_sha,
            "detail": "idempotent merge replay",
            "fence_token": proposal.merge_fence_token,
            "recovery_required": proposal.recovery_required,
        }

    if proposal.status != "in_review":
        raise GitOrchestratorError(
            "INVALID_STATE",
            f"proposal is already {proposal.status}",
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
    if mr_iid is None:
        raise GitOrchestratorError(
            "INVALID_STATE",
            "proposal has no associated merge request",
        )

    target_branch = proposal.proposal_data.get("target_branch", "main")
    if _target_recovery_active(db, proposal.space_id, target_branch):
        raise GitOrchestratorError(
            "RECOVERY_REQUIRED",
            "target has unresolved merge recovery; reconcile before new merges",
        )

    if decision.state != "recorded":
        raise GitOrchestratorError(
            "INVALID_STATE",
            f"decision is already {decision.state}",
        )

    # Verify live target HEAD matches proposal base before merging.
    branch = adapter.get_branch(proposal.space_id, target_branch)
    head_sha = branch.get("commit", {}).get("id", "")
    if head_sha and head_sha != proposal.base_sha:
        raise GitOrchestratorError(
            "BASE_MISMATCH",
            f"target HEAD {head_sha} does not match proposal base_sha {proposal.base_sha}",
        )

    # Commit the durability barrier before the external merge call.
    fence_token = _next_fence_token(db, proposal.space_id, target_branch)
    proposal.merge_fence_token = fence_token
    proposal.recovery_required = True
    decision.state = "merge_attempted"
    db.flush()
    db.commit()

    trailers = (
        f"Decision-ID: {decision.id}\n"
        f"Decision-Note-ID: {decision.note_id}\n"
        f"Decision-Hash: {decision.record_sha256}\n"
        f"Approved-by: {decision.actor_id}"
    )
    merge_message = f"Merge proposal {proposal.id}\n\n{trailers}"

    try:
        result = adapter.merge_merge_request(
            proposal.space_id,
            mr_iid,
            proposal.proposal_sha,
            merge_commit_message=merge_message,
        )
        merge_sha = result.get("merge_commit_sha") or result.get("sha")
        if merge_sha is None:
            raise GitOrchestratorError(
                "MERGE_FAILED",
                "GitLab merge response missing merge commit SHA",
            )

        # Verify the merge commit exists and has correct parentage.
        commit = adapter.get_commit(proposal.space_id, merge_sha)
        parents = commit.get("parent_ids", [])
        if (
            len(parents) < 2
            or parents[0] != proposal.base_sha
            or parents[1] != proposal.proposal_sha
        ):
            raise GitOrchestratorError(
                "MERGE_PARENT_MISMATCH",
                f"merge commit parents {parents} do not match base/proposal",
            )

        proposal.status = "merged"
        proposal.target_sha = merge_sha
        decision.state = "merged"
        proposal.recovery_required = False
        db.flush()
        db.commit()

        return {
            "proposal_id": proposal.id,
            "status": "merged",
            "merge_sha": merge_sha,
            "detail": "merged via GitLab with verified parentage",
            "fence_token": fence_token,
            "recovery_required": proposal.recovery_required,
        }
    except (GitLabAdapterError, httpx.HTTPError) as exc:
        # Unknown outcome: leave recovery_required=True and quarantine.
        decision.state = "quarantined"
        db.flush()
        db.commit()
        raise GitOrchestratorError(
            "MERGE_UNKNOWN_OUTCOME",
            f"GitLab merge call failed; outcome unknown, target quarantined: {exc}",
        ) from exc
    except GitOrchestratorError as exc:
        if exc.code in ("MERGE_PARENT_MISMATCH", "MERGE_FAILED"):
            # Post-call verification failed: outcome is ambiguous, not proven failed.
            # ADR-13 §7: only conclusive no-merge evidence may clear the barrier.
            decision.state = "quarantined"
            db.flush()
            db.commit()
        raise


def reconcile_merge(
    db: Session,
    adapter: GitLabAdapter,
    proposal_id: uuid.UUID,
) -> dict[str, Any]:
    """Reconcile a quarantined merge attempt using Git-derived evidence."""
    proposal = db.get(ProposalRecord, proposal_id)
    if proposal is None:
        raise GitOrchestratorError("NOT_FOUND", "proposal not found")

    decision = (
        db.query(DecisionRecord).filter_by(proposal_id=proposal.id, outcome="accepted").first()
    )
    if decision is None:
        raise GitOrchestratorError("NOT_FOUND", "no accepted decision for this proposal")

    if decision.state not in ("quarantined", "merge_attempted"):
        raise GitOrchestratorError(
            "INVALID_STATE",
            f"decision is {decision.state}, not quarantined or merge_attempted",
        )

    mr_iid = proposal.proposal_data.get("mr_iid")
    if mr_iid is None:
        raise GitOrchestratorError("INVALID_STATE", "proposal has no associated merge request")

    # Try to find a merge commit for this proposal in the target branch.
    target_branch = proposal.proposal_data.get("target_branch", "main")
    branch = adapter.get_branch(proposal.space_id, target_branch)
    head_sha = branch.get("commit", {}).get("id", "")

    # Walk back a small window looking for a merge commit with matching parents.
    candidate_shas = [head_sha]
    for _ in range(10):
        next_shas = []
        for sha in candidate_shas:
            commit = adapter.get_commit(proposal.space_id, sha)
            parents = commit.get("parent_ids", [])
            if len(parents) >= 2 and parents[1] == proposal.proposal_sha:
                # Found a merge commit whose second parent is our proposal.
                if parents[0] == proposal.base_sha:
                    decision.state = "merged"
                    proposal.status = "merged"
                    proposal.target_sha = sha
                    proposal.recovery_required = False
                    db.flush()
                    db.commit()
                    return {
                        "proposal_id": proposal.id,
                        "status": "merged",
                        "merge_sha": sha,
                        "detail": "reconciled from Git: merge commit found with correct parentage",
                    }
                decision.state = "conflicted"
                proposal.status = "conflicted"
                proposal.recovery_required = False
                db.flush()
                db.commit()
                return {
                    "proposal_id": proposal.id,
                    "status": "conflicted",
                    "merge_sha": sha,
                    "detail": "merge commit found but first parent does not match base",
                }
            next_shas.extend(parents)
        candidate_shas = next_shas
        if not candidate_shas:
            break

    # No merge commit found within the window: outcome is still unknown.
    # ADR-13 §7: only conclusive no-merge evidence may set failed.
    # A bounded search cannot prove absence; keep quarantine.
    decision.state = "quarantined"
    db.flush()
    db.commit()
    return {
        "proposal_id": proposal.id,
        "status": "quarantined",
        "merge_sha": None,
        "detail": "merge outcome still unknown; manual investigation required",
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
