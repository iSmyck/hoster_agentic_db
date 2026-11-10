"""Unit tests for the Session service business logic."""

from __future__ import annotations

import time

import pytest
from sqlalchemy.orm import Session

from session.app.services import session_service
from session.app.services.session_service import SessionServiceError


@pytest.fixture
def stable_id() -> str:
    return "test:alice"


class TestCreateSession:
    def test_create_returns_tokens_and_persists_row(
        self,
        db_session: Session,
        stable_id: str,
    ) -> None:
        pair = session_service.create_session(db_session, stable_id)
        assert pair.access_token
        assert pair.refresh_token
        assert pair.stable_id == stable_id

        row = db_session.get(session_service.SessionRecord, pair.session_id)
        assert row is not None
        assert row.stable_id == stable_id
        assert row.revoked_at is None

    def test_create_rejects_empty_stable_id(self, db_session: Session) -> None:
        with pytest.raises(SessionServiceError) as exc_info:
            session_service.create_session(db_session, "")
        assert exc_info.value.code == "INVALID_IDENTITY"


class TestValidateAccessToken:
    def test_valid_token_returns_identity_and_revisions(
        self,
        db_session: Session,
        stable_id: str,
    ) -> None:
        pair = session_service.create_session(
            db_session,
            stable_id,
            access_policy_revision="a" * 40,
            approval_policy_revision="b" * 40,
        )
        result = session_service.validate_access_token(db_session, pair.access_token)
        assert result.stable_id == stable_id
        assert result.access_policy_revision == "a" * 40
        assert result.approval_policy_revision == "b" * 40

    def test_expired_token_rejected(
        self,
        db_session: Session,
        stable_id: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(session_service.settings, "ACCESS_TTL_SECONDS", -1)
        pair = session_service.create_session(db_session, stable_id)
        with pytest.raises(SessionServiceError) as exc_info:
            session_service.validate_access_token(db_session, pair.access_token)
        assert exc_info.value.code == "TOKEN_EXPIRED"

    def test_revoked_token_rejected(
        self,
        db_session: Session,
        stable_id: str,
    ) -> None:
        pair = session_service.create_session(db_session, stable_id)
        session_service.revoke_session(db_session, pair.access_token)
        with pytest.raises(SessionServiceError) as exc_info:
            session_service.validate_access_token(db_session, pair.access_token)
        assert exc_info.value.code == "TOKEN_REVOKED"

    def test_refresh_token_rejected_as_access(
        self,
        db_session: Session,
        stable_id: str,
    ) -> None:
        pair = session_service.create_session(db_session, stable_id)
        with pytest.raises(SessionServiceError) as exc_info:
            session_service.validate_access_token(db_session, pair.refresh_token)
        assert exc_info.value.code == "TOKEN_INVALID"

    def test_tampered_token_rejected(self, db_session: Session) -> None:
        with pytest.raises(SessionServiceError) as exc_info:
            session_service.validate_access_token(db_session, "not-a-token")
        assert exc_info.value.code == "TOKEN_INVALID"


class TestRefreshAccessToken:
    def test_refresh_issues_new_access_token(
        self,
        db_session: Session,
        stable_id: str,
    ) -> None:
        pair = session_service.create_session(db_session, stable_id)
        time.sleep(0.01)
        refreshed = session_service.refresh_access_token(db_session, pair.refresh_token)
        assert refreshed.access_token != pair.access_token
        assert refreshed.refresh_token == pair.refresh_token

        # Old access token is invalidated because the access JTI rotated.
        with pytest.raises(SessionServiceError) as exc_info:
            session_service.validate_access_token(db_session, pair.access_token)
        assert exc_info.value.code == "TOKEN_REVOKED"

        # New access token validates.
        result = session_service.validate_access_token(db_session, refreshed.access_token)
        assert result.stable_id == stable_id

    def test_refresh_with_access_token_rejected(
        self,
        db_session: Session,
        stable_id: str,
    ) -> None:
        pair = session_service.create_session(db_session, stable_id)
        with pytest.raises(SessionServiceError) as exc_info:
            session_service.refresh_access_token(db_session, pair.access_token)
        assert exc_info.value.code == "TOKEN_INVALID"


class TestRevokeAll:
    def test_revoke_all_for_user(
        self,
        db_session: Session,
        stable_id: str,
    ) -> None:
        pair1 = session_service.create_session(db_session, stable_id)
        pair2 = session_service.create_session(db_session, stable_id)
        other = session_service.create_session(db_session, "test:bob")

        count = session_service.revoke_all_for_user(db_session, stable_id)
        assert count == 2

        with pytest.raises(SessionServiceError) as exc_info:
            session_service.validate_access_token(db_session, pair1.access_token)
        assert exc_info.value.code == "TOKEN_REVOKED"

        with pytest.raises(SessionServiceError) as exc_info:
            session_service.validate_access_token(db_session, pair2.access_token)
        assert exc_info.value.code == "TOKEN_REVOKED"

        # Other user's session remains valid.
        result = session_service.validate_access_token(db_session, other.access_token)
        assert result.stable_id == "test:bob"


class TestLogout:
    def test_logout_revokes_session(
        self,
        db_session: Session,
        stable_id: str,
    ) -> None:
        pair = session_service.create_session(db_session, stable_id)
        session_service.logout(db_session, pair.access_token)
        with pytest.raises(SessionServiceError) as exc_info:
            session_service.validate_access_token(db_session, pair.access_token)
        assert exc_info.value.code == "TOKEN_REVOKED"
