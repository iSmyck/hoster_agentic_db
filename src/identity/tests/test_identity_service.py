"""Synthetic unit tests for identity_service functions that depend on adapters."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from identity.app.models.authz import GroupSnapshot, Revocation
from identity.app.services import identity_service


@pytest.fixture
def external_ref() -> dict[str, str]:
    return {"issuer": "test", "sub": "alice"}


@pytest.fixture
def mock_adapter(external_ref: dict[str, str]) -> MagicMock:
    adapter = MagicMock()
    adapter.resolve_external_refs.return_value = external_ref
    return adapter


class TestRecheckGroupMembership:
    def test_expires_only_matching_snapshots_and_advances_epoch(
        self,
        db_session: Session,
        mock_adapter: MagicMock,
        external_ref: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_adapter.fetch_groups.return_value = ["authors"]
        monkeypatch.setattr(
            identity_service, "_get_identity_adapter", lambda: mock_adapter
        )

        space_id = f"space-{uuid.uuid4().hex[:8]}"
        other_ref = {"issuer": "test", "sub": "bob"}

        # Seed: one matching snapshot and one for a different user.
        db_session.add(
            GroupSnapshot(
                space_id=space_id,
                group_name="readers",
                member_refs=[external_ref],
                parent_groups=[],
            )
        )
        db_session.add(
            GroupSnapshot(
                space_id=space_id,
                group_name="readers",
                member_refs=[other_ref],
                parent_groups=[],
            )
        )
        db_session.commit()

        result = identity_service.recheck_group_membership(
            db_session, space_id, "token"
        )

        assert result["space_id"] == space_id
        assert result["groups"] == ["authors"]
        assert result["groups_ingested"] == 1

        active = (
            db_session.query(GroupSnapshot)
            .filter(
                GroupSnapshot.space_id == space_id,
                GroupSnapshot.valid_until.is_(None),
            )
            .all()
        )
        active_names = {s.group_name for s in active}
        # The new authors snapshot plus the other user's readers snapshot remain.
        assert active_names == {"authors", "readers"}

        # The other user's snapshot must remain valid.
        other_still_active = [
            s
            for s in active
            if s.member_refs and s.member_refs[0].get("sub") == "bob"
        ]
        assert len(other_still_active) == 1

        expired = (
            db_session.query(GroupSnapshot)
            .filter(
                GroupSnapshot.space_id == space_id,
                GroupSnapshot.valid_until.is_not(None),
            )
            .all()
        )
        assert len(expired) == 1
        assert expired[0].member_refs == [external_ref]

        revocation = (
            db_session.query(Revocation)
            .filter(Revocation.space_id == space_id)
            .first()
        )
        assert revocation is not None
        assert revocation.revoked_at_epoch == result["epoch"]
        assert revocation.revoked_at_epoch > 0

    def test_expires_snapshot_with_extra_claims(
        self,
        db_session: Session,
        mock_adapter: MagicMock,
        external_ref: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Membership matching is keyed by issuer+sub; extra claims must not break expiration."""
        mock_adapter.fetch_groups.return_value = ["authors"]
        monkeypatch.setattr(
            identity_service, "_get_identity_adapter", lambda: mock_adapter
        )

        space_id = f"space-{uuid.uuid4().hex[:8]}"
        # Stored snapshot includes extra claims that the current adapter output may omit.
        stored_ref = {**external_ref, "email": "alice@example.com", "preferred_username": "alice"}

        db_session.add(
            GroupSnapshot(
                space_id=space_id,
                group_name="readers",
                member_refs=[stored_ref],
                parent_groups=[],
            )
        )
        db_session.commit()

        result = identity_service.recheck_group_membership(
            db_session, space_id, "token"
        )

        assert result["groups"] == ["authors"]

        active = (
            db_session.query(GroupSnapshot)
            .filter(
                GroupSnapshot.space_id == space_id,
                GroupSnapshot.valid_until.is_(None),
            )
            .all()
        )
        active_names = {s.group_name for s in active}
        # Only the new authors snapshot remains; the readers snapshot with extra claims expired.
        assert active_names == {"authors"}

        expired = (
            db_session.query(GroupSnapshot)
            .filter(
                GroupSnapshot.space_id == space_id,
                GroupSnapshot.valid_until.is_not(None),
            )
            .all()
        )
        assert len(expired) == 1

    def test_advances_epoch_even_for_empty_groups(
        self,
        db_session: Session,
        mock_adapter: MagicMock,
        external_ref: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_adapter.fetch_groups.return_value = []
        monkeypatch.setattr(
            identity_service, "_get_identity_adapter", lambda: mock_adapter
        )

        space_id = f"space-{uuid.uuid4().hex[:8]}"
        db_session.add(
            GroupSnapshot(
                space_id=space_id,
                group_name="readers",
                member_refs=[external_ref],
                parent_groups=[],
            )
        )
        db_session.commit()

        result = identity_service.recheck_group_membership(
            db_session, space_id, "token"
        )

        assert result["groups"] == []
        assert result["groups_ingested"] == 0

        revocation = (
            db_session.query(Revocation)
            .filter(Revocation.space_id == space_id)
            .first()
        )
        assert revocation is not None
        assert revocation.revoked_at_epoch == result["epoch"]
