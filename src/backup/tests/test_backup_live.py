"""Live integration tests for the Backup adapter.

These tests require a running GitLab sandbox and are skipped by default.
Set ``RUN_LIVE_BACKUP_TESTS=1`` to enable them.
"""

from __future__ import annotations

import os

import pytest

from backup.app.adapters.gitlab import HttpBackupGitLabAdapter
from backup.app.core.config import settings
from backup.app.services.backup import BackupService

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_BACKUP_TESTS") != "1",
    reason="live backup tests disabled; set RUN_LIVE_BACKUP_TESTS=1",
)


@pytest.fixture
def live_service() -> BackupService:
    adapter = HttpBackupGitLabAdapter(
        settings.BACKUP_GITLAB_URL,
        settings.BACKUP_GITLAB_TOKEN,
        settings.BACKUP_GITLAB_PROJECT_PATH_PREFIX,
    )
    return BackupService(adapter=adapter)


def test_live_mirror_backup(live_service: BackupService) -> None:
    space_id = os.environ.get("BACKUP_LIVE_SPACE_ID", settings.BACKUP_GITLAB_PROJECT_PATH_PREFIX.strip("/") or "live-space")
    package = live_service.create_mirror_backup(space_id)
    assert package.status == "complete"
