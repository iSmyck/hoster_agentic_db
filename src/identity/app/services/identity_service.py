"""Identity + AuthZ business logic.

The service layer depends only on repository-level models and the configured
policy contract. No HTTP or IdP details leak in here.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from identity.app.adapters.keycloak import IdentityAdapterError, KeycloakIdentityAdapter
from identity.app.core.config import settings
from identity.app.models.authz import (
    AuthzContext,
    GroupSnapshot,
    Identity,
    IdentityExternalRef,
    PolicyBundle,
    Revocation,
)


class IdentityServiceError(Exception):
    """Domain error raised by identity services."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_ref(external_ref: Any) -> dict[str, Any]:
    """Normalize an external reference to a plain dict."""
    if hasattr(external_ref, "model_dump"):
        return external_ref.model_dump()
    return dict(external_ref)


def _ref_matches(stored: dict[str, Any], requested: dict[str, Any]) -> bool:
    """Check whether requested ref matches a stored ref.

    The stored ref is treated as a subset filter: every key present in the
    stored ref must equal the corresponding key in the requested ref. An
    empty requested ref is intentionally a non-match to avoid matching all
    identities when no ref is supplied.

    For group membership, the stored ref must contain both ``issuer`` and
    ``sub`` so that a bare ``sub`` cannot match across identity providers.
    """
    if not requested:
        return False
    if not stored:
        return False
    if "issuer" not in stored or "sub" not in stored:
        return False
    return all(requested.get(k) == v for k, v in stored.items())


def _member_ref_matches(stored: dict[str, Any], requested: dict[str, Any]) -> bool:
    """Check whether two member refs identify the same subject.

    Group membership is keyed by ``issuer`` + ``sub`` only. Extra claims
    that an adapter may add or remove over time (email, preferred_username,
    etc.) must not break matching of previously ingested snapshots.
    """
    if not isinstance(stored, dict) or not isinstance(requested, dict):
        return False
    if "issuer" not in stored or "sub" not in stored:
        return False
    if "issuer" not in requested or "sub" not in requested:
        return False
    return stored["issuer"] == requested["issuer"] and stored["sub"] == requested["sub"]


_VALID_ACTOR_TYPES = {"human", "agent", "connector", "internal_ci"}


def resolve_identity(
    db: Session,
    external_ref: Any,
) -> Identity:
    """Find or create a stable Identity by external reference.

    Uses a normalized, uniquely-constrained lookup table so the query is
    indexed on both PostgreSQL and SQLite and concurrent resolves are
    deterministic.
    """
    ref = _normalize_ref(external_ref)
    issuer = ref.get("issuer")
    sub = ref.get("sub")
    if not issuer or not sub:
        raise IdentityServiceError(
            "INVALID_IDENTITY_REF",
            "external_ref must contain 'issuer' and 'sub'",
        )

    link = db.get(IdentityExternalRef, (issuer, sub))
    if link is not None:
        identity = db.get(Identity, link.identity_id)
        if identity is not None:
            return identity

    identity = Identity(external_refs=[ref])
    db.add(identity)
    db.flush()

    # Deterministic upsert: the unique (issuer, sub) constraint guarantees that
    # a concurrent resolve leaves only one link row. On conflict we roll back
    # our pending insert and resolve to the winner.
    db.add(IdentityExternalRef(identity_id=identity.id, issuer=issuer, sub=sub))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        link = db.get(IdentityExternalRef, (issuer, sub))
        if link is None:
            raise
        if str(link.identity_id) != str(identity.id):
            identity = db.get(Identity, link.identity_id)
            if identity is None:
                raise IdentityServiceError("NOT_FOUND", "linked identity missing")
    return identity


def _get_identity_adapter() -> KeycloakIdentityAdapter:
    """Return the configured upstream identity adapter."""
    adapter_name = settings.IDENTITY_ADAPTER.lower()
    if adapter_name == "keycloak":
        return KeycloakIdentityAdapter(
            keycloak_url=settings.KEYCLOAK_URL,
            realm=settings.KEYCLOAK_REALM,
            client_id=settings.KEYCLOAK_CLIENT_ID,
            client_secret=settings.KEYCLOAK_CLIENT_SECRET,
        )
    if adapter_name == "stub":
        raise IdentityServiceError(
            "IDENTITY_ADAPTER_NOT_AVAILABLE",
            "The stub adapter cannot resolve tokens",
        )
    raise IdentityServiceError(
        "UNKNOWN_IDENTITY_ADAPTER",
        f"Unknown identity adapter: {settings.IDENTITY_ADAPTER!r}",
    )


def resolve_identity_from_token(
    db: Session,
    access_token: str,
) -> Identity:
    """Resolve a stable Identity from a bearer access token.

    Uses the configured upstream adapter to normalize the token into an
    external_ref and then delegates to :func:`resolve_identity`.
    """
    adapter = _get_identity_adapter()
    try:
        external_ref = adapter.resolve_external_refs(access_token)
    except IdentityAdapterError as exc:
        raise IdentityServiceError(
            f"IDENTITY_ADAPTER_ERROR:{exc.code}",
            exc.message,
        ) from exc
    return resolve_identity(db, external_ref)


def fetch_upstream_groups(
    access_token: str,
) -> list[str]:
    """Return upstream group memberships for a bearer token.

    Raises IdentityServiceError on adapter failure or invalid token.
    """
    adapter = _get_identity_adapter()
    try:
        return adapter.fetch_groups(access_token)
    except IdentityAdapterError as exc:
        raise IdentityServiceError(
            f"IDENTITY_ADAPTER_ERROR:{exc.code}",
            exc.message,
        ) from exc


def recheck_group_membership(
    db: Session,
    space_id: str,
    access_token: str,
) -> dict[str, Any]:
    """Recheck upstream groups and update the subject's membership in a Space.

    Used before sensitive operations (merge, export, closed-page read) to
    enforce the revocation barrier.  Only the token subject's memberships are
    updated; other users' snapshots are preserved.  Empty membership revokes
    the subject's previous groups and advances the Space epoch.
    """
    adapter = _get_identity_adapter()
    try:
        external_ref = adapter.resolve_external_refs(access_token)
        groups = adapter.fetch_groups(access_token)
    except IdentityAdapterError as exc:
        raise IdentityServiceError(
            f"IDENTITY_ADAPTER_ERROR:{exc.code}",
            exc.message,
        ) from exc

    epoch = _next_space_epoch(db, space_id)
    now = _now()

    # Expire only the subject's previous memberships, not the whole Space.
    # Filter in Python to avoid SQLAlchemy JSON operator deprecation; spaces
    # have a bounded number of group snapshots.
    active_snapshots = (
        db.query(GroupSnapshot)
        .filter(
            and_(
                GroupSnapshot.space_id == space_id,
                GroupSnapshot.valid_until.is_(None),
            )
        )
        .all()
    )
    snapshot_ids_to_expire = [
        snap.id
        for snap in active_snapshots
        if any(_member_ref_matches(member, external_ref) for member in (snap.member_refs or []))
    ]
    if snapshot_ids_to_expire:
        db.query(GroupSnapshot).filter(GroupSnapshot.id.in_(snapshot_ids_to_expire)).update(
            {"valid_until": now}, synchronize_session=False
        )

    rows: list[GroupSnapshot] = []
    for group_name in groups:
        row = GroupSnapshot(
            space_id=space_id,
            group_name=group_name,
            member_refs=[external_ref],
            parent_groups=[],
            epoch=epoch,
        )
        db.add(row)
        rows.append(row)

    # Always advance the epoch, even for empty membership, so revocation
    # propagates and stale contexts are invalidated.
    db.add(
        Revocation(
            space_id=space_id,
            revoked_at_epoch=epoch,
            reason="group_membership_recheck",
        )
    )
    db.flush()
    return {
        "space_id": space_id,
        "epoch": epoch,
        "groups": groups,
        "groups_ingested": len(rows),
    }


def _next_space_epoch(db: Session, space_id: str) -> int:
    """Return the next monotonic epoch for a Space."""
    max_epoch = db.query(func.max(GroupSnapshot.epoch)).filter(
        GroupSnapshot.space_id == space_id
    ).scalar() or 0
    policy_epoch = db.query(func.max(PolicyBundle.activation_epoch)).filter(
        PolicyBundle.space_id == space_id
    ).scalar() or 0
    revocation_epoch = db.query(func.max(Revocation.revoked_at_epoch)).filter(
        Revocation.space_id == space_id
    ).scalar() or 0
    return max(max_epoch, policy_epoch, revocation_epoch) + 1


def ingest_group_snapshot(
    db: Session,
    space_id: str,
    snapshot: Any,
) -> list[GroupSnapshot]:
    """Store a new group snapshot for a Space and bump the Space epoch.

    ``snapshot`` may be a Pydantic model or dict with a ``groups`` list.
    """
    data = snapshot.model_dump() if hasattr(snapshot, "model_dump") else dict(snapshot)
    groups = data.get("groups", [])
    if not groups:
        raise IdentityServiceError("INVALID_SNAPSHOT", "snapshot must contain at least one group")

    epoch = _next_space_epoch(db, space_id)
    now = _now()

    # Mark previous snapshots as superseded.
    db.query(GroupSnapshot).filter(
        and_(GroupSnapshot.space_id == space_id, GroupSnapshot.valid_until.is_(None))
    ).update({"valid_until": now}, synchronize_session=False)

    rows: list[GroupSnapshot] = []
    for group in groups:
        member_refs = [
            _normalize_ref(m) for m in group.get("member_refs", [])
        ]
        row = GroupSnapshot(
            space_id=space_id,
            group_name=group["group_name"],
            member_refs=member_refs,
            parent_groups=group.get("parent_groups", []),
            epoch=epoch,
        )
        db.add(row)
        rows.append(row)

    db.flush()
    return rows


def activate_policy_bundle(
    db: Session,
    space_id: str,
    bundle: Any,
) -> PolicyBundle:
    """Activate an access+approval policy bundle for a Space."""
    data = bundle.model_dump() if hasattr(bundle, "model_dump") else dict(bundle)
    required = {
        "bundle_id",
        "repository_id",
        "access_policy_revision",
        "approval_policy_revision",
    }
    missing = required - set(data.keys())
    if missing:
        raise IdentityServiceError("INVALID_POLICY", f"missing fields: {sorted(missing)}")

    epoch = _next_space_epoch(db, space_id)
    now = _now()

    # Mark previous bundles as superseded.
    db.query(PolicyBundle).filter(
        and_(PolicyBundle.space_id == space_id, PolicyBundle.valid_until.is_(None))
    ).update({"valid_until": now}, synchronize_session=False)

    policy_data = {
        "bundle_id": data["bundle_id"],
        "repository_id": data["repository_id"],
        "access_policy_revision": data["access_policy_revision"],
        "approval_policy_revision": data["approval_policy_revision"],
        "group_capabilities": data.get("group_capabilities", {}),
        "path_approvers": data.get("path_approvers", {}),
    }

    row = PolicyBundle(
        space_id=space_id,
        policy_data=policy_data,
        activation_epoch=epoch,
    )
    db.add(row)
    db.flush()

    # Activation implicitly increments revocation epoch so old contexts stale.
    db.add(
        Revocation(
            space_id=space_id,
            revoked_at_epoch=epoch,
            reason="policy_bundle_activated",
        )
    )
    return row


def _active_group_snapshots(db: Session, space_id: str) -> list[GroupSnapshot]:
    return (
        db.query(GroupSnapshot)
        .filter(
            and_(
                GroupSnapshot.space_id == space_id,
                GroupSnapshot.valid_until.is_(None),
            )
        )
        .all()
    )


def _active_policy_bundle(db: Session, space_id: str) -> PolicyBundle | None:
    return (
        db.query(PolicyBundle)
        .filter(
            and_(
                PolicyBundle.space_id == space_id,
                PolicyBundle.valid_until.is_(None),
            )
        )
        .order_by(desc(PolicyBundle.activation_epoch))
        .first()
    )


def _latest_revocation_epoch(db: Session, space_id: str) -> int:
    epoch = (
        db.query(func.max(Revocation.revoked_at_epoch))
        .filter(Revocation.space_id == space_id)
        .scalar()
    )
    return epoch or 0


def _resolve_groups_for_actor(
    snapshots: list[GroupSnapshot],
    actor_ref: dict[str, Any],
) -> set[str]:
    """Return effective (direct + nested) group names for an actor ref."""
    direct: set[str] = set()
    for snap in snapshots:
        for member in snap.member_refs or []:
            if _member_ref_matches(member, actor_ref):
                direct.add(snap.group_name)

    # Build parent -> children map and compute transitive closure.
    children: dict[str, set[str]] = {}
    for snap in snapshots:
        for parent in snap.parent_groups or []:
            children.setdefault(parent, set()).add(snap.group_name)

    effective = set(direct)
    queue: deque[str] = deque(direct)
    while queue:
        current = queue.popleft()
        for child in children.get(current, set()):
            if child not in effective:
                effective.add(child)
                queue.append(child)
    return effective


def _membership_sha256(snapshots: list[GroupSnapshot]) -> str:
    """Deterministic SHA-256 over sorted group membership data."""
    payload = []
    for snap in sorted(snapshots, key=lambda s: s.group_name):
        members = sorted(
            (m.get("issuer", ""), m.get("sub", "")) for m in (snap.member_refs or [])
        )
        parents = sorted(snap.parent_groups or [])
        payload.append({
            "group_name": snap.group_name,
            "member_refs": members,
            "parent_groups": parents,
        })
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def compute_authz_context(
    db: Session,
    space_id: str,
    actor_id: uuid.UUID,
    actor_type: str = "human",
) -> AuthzContext:
    """Compute and persist an AuthzContext for an actor in a Space."""
    if actor_type not in _VALID_ACTOR_TYPES:
        raise IdentityServiceError(
            "INVALID_ACTOR_TYPE",
            f"unknown actor_type: {actor_type!r}",
        )

    identity = db.get(Identity, actor_id)
    if identity is None:
        raise IdentityServiceError("NOT_FOUND", "actor identity not found")

    snapshots = _active_group_snapshots(db, space_id)
    if not snapshots:
        raise IdentityServiceError("GROUP_SNAPSHOT_STALE", "no active group snapshot for space")

    bundle = _active_policy_bundle(db, space_id)
    if bundle is None:
        raise IdentityServiceError("POLICY_REVISION_MISMATCH", "no active policy bundle for space")

    actor_ref = identity.external_refs[0] if identity.external_refs else {}
    effective_groups = _resolve_groups_for_actor(snapshots, actor_ref)

    capabilities: set[str] = set()
    for group in effective_groups:
        capabilities.update(bundle.policy_data.get("group_capabilities", {}).get(group, []))

    # Enforce actor-type capability guardrails from the contract.
    allowed = _allowed_capabilities(actor_type)
    capabilities = capabilities & allowed

    path_scopes: list[dict[str, Any]] = []
    for group in effective_groups:
        for prefix in bundle.policy_data.get("path_approvers", {}).get(group, []):
            path_scopes.append({
                "space_id": space_id,
                "path_prefix": _normalize_path(prefix),
                "capabilities": ["propose"],
            })

    evaluated_at = _now()
    expires_at = evaluated_at + timedelta(seconds=settings.CONTEXT_TTL_SECONDS)
    revocation_epoch = _latest_revocation_epoch(db, space_id)
    snapshot_id = uuid.uuid4()
    membership_sha256 = _membership_sha256(snapshots)

    stable_id = f"{actor_ref.get('issuer', 'unknown')}:{actor_ref.get('sub', str(identity.id))}"

    space_scope = {
        "space_id": space_id,
        "repository_id": bundle.policy_data.get("repository_id", space_id),
        "capabilities": sorted(capabilities),
        "policy_bundle_id": bundle.policy_data.get("bundle_id", "unknown"),
        "access_policy_revision": bundle.policy_data.get("access_policy_revision", ""),
        "approval_policy_revision": bundle.policy_data.get("approval_policy_revision", ""),
        "group_snapshot": {
            "snapshot_id": str(snapshot_id),
            "captured_at": evaluated_at.isoformat(),
            "membership_sha256": membership_sha256,
            "groups": [
                {
                    "group_id": snap.group_name,
                    "membership_source": "direct" if snap.group_name in effective_groups else "nested",
                }
                for snap in snapshots
                if snap.group_name in effective_groups
            ],
        },
        "revocation_epoch": revocation_epoch,
    }

    computed = {
        "schema_version": "authz-context-v2",
        "context_id": str(uuid.uuid4()),
        "issuer": settings.ISSUER,
        "stable_id": stable_id,
        "actor_type": actor_type,
        "space_scopes": [space_scope],
        "path_scopes": path_scopes,
        "evaluated_at": evaluated_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "revocation_epoch": revocation_epoch,
    }

    context = AuthzContext(
        space_id=space_id,
        actor_id=actor_id,
        computed_context=computed,
        epoch=revocation_epoch,
    )
    db.add(context)
    db.flush()
    return context


def _allowed_capabilities(actor_type: str) -> set[str]:
    """Return capability universe for a given actor type (contract guard)."""
    if actor_type in ("agent", "connector"):
        return {"read", "search", "propose", "source_read"}
    if actor_type == "internal_ci":
        return {"read", "index_write"}
    return {
        "read",
        "search",
        "propose",
        "review",
        "merge",
        "export",
        "manage_grants",
        "source_read",
        "index_write",
    }


def _normalize_path(path: str) -> str:
    """Normalize a path prefix to absolute form without '..' or trailing slash."""
    p = path.replace("\\", "/")
    if not p.startswith("/"):
        p = "/" + p
    parts = [part for part in p.split("/") if part and part != "."]
    if ".." in parts:
        raise IdentityServiceError("INVALID_PATH", "path must not contain '..'")
    if not parts:
        return "/"
    return "/" + "/".join(parts)


def check_path_approval(
    db: Session,
    space_id: str,
    actor_id: uuid.UUID,
    path: str,
) -> dict[str, Any]:
    """Check whether actor can approve a path using longest-prefix matching."""
    normalized = _normalize_path(path)

    identity = db.get(Identity, actor_id)
    if identity is None:
        return {
            "approved": False,
            "space_id": space_id,
            "actor_id": actor_id,
            "path": path,
            "matched_prefix": None,
            "reason": "actor identity not found",
        }

    snapshots = _active_group_snapshots(db, space_id)
    bundle = _active_policy_bundle(db, space_id)
    if bundle is None:
        return {
            "approved": False,
            "space_id": space_id,
            "actor_id": actor_id,
            "path": path,
            "matched_prefix": None,
            "reason": "no active policy bundle for space",
        }

    actor_ref = identity.external_refs[0] if identity.external_refs else {}
    effective_groups = _resolve_groups_for_actor(snapshots, actor_ref)

    approver_map: dict[str, list[str]] = bundle.policy_data.get("path_approvers", {})

    matched_prefix: str | None = None
    matched_groups: set[str] = set()
    for group, prefixes in approver_map.items():
        if group not in effective_groups:
            continue
        for prefix in prefixes:
            np = _normalize_path(prefix)
            if normalized == np or normalized.startswith(np + "/") or (np == "/"):
                if matched_prefix is None or len(np) > len(matched_prefix):
                    matched_prefix = np
                    matched_groups = {group}
                elif len(np) == len(matched_prefix):
                    matched_groups.add(group)

    approved = bool(matched_prefix and matched_groups)
    return {
        "approved": approved,
        "space_id": space_id,
        "actor_id": actor_id,
        "path": path,
        "matched_prefix": matched_prefix,
        "reason": "approved" if approved else "no matching approver group for path",
    }
