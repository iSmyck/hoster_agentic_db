"""Live smoke test for the Backup adapter.

Usage:
    RUN_LIVE_BACKUP_TESTS=1 PYTHONPATH=src uv run python src/backup/scripts/smoke_backup.py

Skips gracefully if the sandbox is unavailable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow the script to run from the repository root without package install.
_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backup.app.adapters.gitlab import HttpBackupGitLabAdapter
from backup.app.core.config import settings
from backup.app.services.backup import BackupService


def main() -> int:
    if os.environ.get("RUN_LIVE_BACKUP_TESTS") != "1":
        print("SKIP: RUN_LIVE_BACKUP_TESTS is not set to 1")
        return 0

    space_id = os.environ.get("BACKUP_LIVE_SPACE_ID", "corp-kb/sales")
    adapter = HttpBackupGitLabAdapter(
        settings.BACKUP_GITLAB_URL,
        settings.BACKUP_GITLAB_TOKEN,
        settings.BACKUP_GITLAB_PROJECT_PATH_PREFIX,
    )
    service = BackupService(adapter=adapter)

    try:
        package = service.create_mirror_backup(space_id)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: backup failed: {exc}")
        return 1

    if package.status != "complete":
        print(f"FAIL: backup status is {package.status}")
        return 1

    manifest = package.manifest
    if manifest is None:
        print("FAIL: manifest missing")
        return 1

    package_path = Path(package.package_path)
    mirror_dir = package_path / "mirror.git"
    if not (mirror_dir / "HEAD").exists():
        print("FAIL: mirror.git/HEAD missing")
        return 1

    for file_hash in manifest.files:
        file_path = package_path / file_hash.path
        if not file_path.exists():
            print(f"FAIL: missing {file_hash.path}")
            return 1

    print(f"PASS: backup {package.backup_id} for {space_id} verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
