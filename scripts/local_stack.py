#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx",
#   "sqlalchemy",
#   "psycopg",
#   "alembic",
#   "pydantic",
#   "pydantic-settings",
# ]
# ///

"""Local development stack orchestrator for corp-ai-db G1 vertical slice.

Starts infrastructure via docker compose, runs Alembic migrations for all
services, seeds synthetic data, then launches Python app services and
Open WebUI on the host.  Use ``--stop`` to tear down.
"""

from __future__ import annotations

import argparse
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=False)
INFRA_COMMAND = ["docker", "compose", "up", "-d"]
INFRA_STOP_COMMAND = ["docker", "compose", "down"]

SERVICES: list[dict[str, Any]] = [
    {
        "name": "identity",
        "port": 8001,
        "module": "identity.app.main:app",
        "migrations": str(REPO_ROOT / "src" / "identity" / "migrations"),
    },
    {
        "name": "session",
        "port": 8004,
        "module": "session.app.main:app",
        "migrations": str(REPO_ROOT / "src" / "session" / "migrations"),
    },
    {
        "name": "go",
        "port": 8002,
        "module": "git_orchestrator.app.main:app",
        "migrations": str(REPO_ROOT / "src" / "git-orchestrator" / "migrations"),
    },
    {
        "name": "retrieval",
        "port": 8003,
        "module": "retrieval.app.main:app",
        "migrations": str(REPO_ROOT / "src" / "retrieval" / "migrations"),
    },
    {
        "name": "backup",
        "port": 8005,
        "module": "backup.app.main:app",
        "migrations": None,
    },
    {
        "name": "kb-ingestion",
        "port": 8006,
        "module": "kb_ingestion.app.main:app",
        "migrations": None,
    },
]

OPENWEBUI_DIR = REPO_ROOT / "_bmad-output" / "test-artifacts" / "t00" / "upstream" / "open-webui"
OPENWEBUI_PORT = 3100


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=REPO_ROOT, check=True, text=True, **kwargs)


def _run_bg(cmd: list[str], **kwargs: Any) -> subprocess.Popen[Any]:
    print(f"$ {' '.join(cmd)} [&]")
    kwargs.setdefault("cwd", REPO_ROOT)
    kwargs.setdefault("text", True)
    return subprocess.Popen(cmd, **kwargs)


def _wait_for_postgres(timeout: float = 60.0) -> None:
    import sqlalchemy

    dsn = os.environ.get("DATABASE_URL", "postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb")
    engine = sqlalchemy.create_engine(dsn)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            print("PostgreSQL is healthy.")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"Waiting for PostgreSQL... ({exc})")
            time.sleep(1)
    raise RuntimeError("PostgreSQL did not become healthy in time")


def _wait_for_keycloak(timeout: float = 60.0) -> None:
    keycloak_url = os.environ.get("KEYCLOAK_URL", "http://localhost:8082").rstrip("/")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{keycloak_url}/realms/master", timeout=5)
            if r.status_code == 200:
                print("Keycloak is healthy.")
                return
        except Exception as exc:  # noqa: BLE001
            print(f"Waiting for Keycloak... ({exc})")
        time.sleep(1)
    raise RuntimeError("Keycloak did not become healthy in time")


def _setup_keycloak() -> dict[str, Any]:
    """Configure the sandbox Keycloak realm and return client secrets."""
    sys.path.insert(0, str(REPO_ROOT / "src" / "identity"))
    from scripts.setup_keycloak import setup_keycloak

    result = setup_keycloak()
    print("Keycloak realm configured.")
    return result


def _run_alembic(migrations_dir: str) -> None:
    from alembic import command
    from alembic.config import Config

    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    cfg = Config()
    cfg.set_main_option("script_location", migrations_dir)
    cfg.set_main_option("version_path_separator", "os")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")
    print(f"Migrations applied: {migrations_dir}")


def _seed_data() -> None:
    """Seed kb_ops drafts/history and create test sessions for G1."""
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker

    sys.path.insert(0, str(REPO_ROOT / "src" / "git-orchestrator"))
    from git_orchestrator.app.adapters.gitlab import StubGitLabAdapter
    from git_orchestrator.app.services.seed import seed_sample_drafts

    dsn = os.environ.get("GO_DATABASE_URL", os.environ["DATABASE_URL"])
    engine = sqlalchemy.create_engine(dsn)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        adapter = StubGitLabAdapter()
        seed_sample_drafts(session, adapter, space_id="corp-kb/sales")
        session.commit()
        print("Seeded kb_ops drafts and stub history.")
    finally:
        session.close()

    # Seed session service tokens for the G1 author and approver.
    sys.path.insert(0, str(REPO_ROOT / "src" / "session"))
    from session.app.services import session_service

    session_engine = sqlalchemy.create_engine(
        os.environ.get("SESSION_DATABASE_URL", os.environ["DATABASE_URL"])
    )
    SessionLocal = sessionmaker(bind=session_engine)
    sess = SessionLocal()
    try:
        for stable_id, role in (("author-1", "user"), ("approver-1", "admin")):
            session_service.create_session(
                sess,
                stable_id=stable_id,
                extra_claims={"role": role},
            )
            print(f"Seeded session token for {stable_id} ({role})")
        sess.commit()
    finally:
        sess.close()


def _start_services() -> list[subprocess.Popen[Any]]:
    processes: list[subprocess.Popen[Any]] = []
    for svc in SERVICES:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        cmd = [
            sys.executable,
            str(REPO_ROOT / "src" / "run_service.py"),
            svc["name"],
            str(svc["port"]),
        ]
        proc = _run_bg(cmd, env=env)
        processes.append(proc)
    return processes


def _openwebui_has_users() -> bool:
    """Check whether Open WebUI's v0.13.0 public.user table already has users."""
    import sqlalchemy

    dsn = os.environ.get("DATABASE_URL", "postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb")
    engine = sqlalchemy.create_engine(dsn)
    try:
        with engine.connect() as conn:
            result = conn.execute(
                sqlalchemy.text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'user')"
                )
            )
            has_table = result.scalar()
            if not has_table:
                return False
            result = conn.execute(sqlalchemy.text("SELECT COUNT(*) FROM public.user"))
            return (result.scalar() or 0) > 0
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: could not check Open WebUI user table: {exc}")
        return False


def _reset_openwebui_users() -> None:
    """Truncate Open WebUI user tables for a clean G1 test run.

    Guarded by G1_ALLOW_DESTRUCTIVE_RESET so a normal ``local_stack.py`` run
    does not wipe manually-created accounts.
    """
    if os.environ.get("G1_ALLOW_DESTRUCTIVE_RESET", "").lower() not in {"1", "true", "yes"}:
        return
    import sqlalchemy

    dsn = os.environ.get("DATABASE_URL", "postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb")
    engine = sqlalchemy.create_engine(dsn)
    try:
        with engine.begin() as conn:
            conn.execute(sqlalchemy.text('TRUNCATE TABLE public."user", public.auth CASCADE'))
        print("Truncated Open WebUI public.user and public.auth tables.")
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: could not truncate Open WebUI user tables: {exc}")


def _load_openwebui_api_env(env: dict[str, str]) -> None:
    """Load KIMI/OpenAI API settings from .env into Open WebUI env vars."""
    try:
        from dotenv import dotenv_values
    except ImportError:
        return

    dot_env = REPO_ROOT / ".env"
    values = dotenv_values(dot_env) if dot_env.exists() else {}
    # Prefer already-exported env vars, then .env values.
    kimi_base = os.environ.get("KIMI_API_BASE_URL") or values.get("KIMI_API_BASE_URL")
    kimi_key = os.environ.get("KIMI_API_KEY") or values.get("KIMI_API_KEY")
    openai_base = os.environ.get("OPENAI_API_BASE_URL") or values.get("OPENAI_API_BASE_URL")
    openai_key = os.environ.get("OPENAI_API_KEY") or values.get("OPENAI_API_KEY")

    if openai_base:
        env["OPENAI_API_BASE_URL"] = openai_base
    elif kimi_base:
        env["OPENAI_API_BASE_URL"] = kimi_base
    if openai_key:
        env["OPENAI_API_KEY"] = openai_key
    elif kimi_key:
        env["OPENAI_API_KEY"] = kimi_key


def _start_openwebui() -> subprocess.Popen[Any] | None:
    if not OPENWEBUI_DIR.exists():
        print(f"Open WebUI checkout not found at {OPENWEBUI_DIR}; skipping.")
        return None
    backend_dir = OPENWEBUI_DIR / "backend"
    venv_python = OPENWEBUI_DIR / ".venv" / "bin" / "python"
    if not venv_python.exists():
        print(f"Open WebUI venv not found at {venv_python}; trying project interpreter.")
        venv_python = Path(sys.executable)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)
    env["PORT"] = str(OPENWEBUI_PORT)
    env["DATABASE_URL"] = os.environ.get("DATABASE_URL", "")
    env["ENABLE_DB_MIGRATIONS"] = "true"
    env["WEBUI_NAME"] = os.environ.get("WEBUI_NAME", "hoster.by Knowledge Base")
    env["ENABLE_DIRECT_CONNECTIONS"] = os.environ.get("ENABLE_DIRECT_CONNECTIONS", "true")
    # The pinned frontend build is produced by `npm run build` in the upstream checkout root.
    env["FRONTEND_BUILD_DIR"] = str(OPENWEBUI_DIR / "build")
    _load_openwebui_api_env(env)

    # Open WebUI v0.13.0 stores users in public.user (not openwebui.user). Always
    # enable auth + signup for G1 local runs and supply the mandatory secret key.
    # RESET_CONFIG_ON_START re-seeds ui.enable_signup from ENABLE_SIGNUP so the
    # first-run signup path is available even when a stale config row exists.
    env["WEBUI_AUTH"] = "true"
    env["ENABLE_SIGNUP"] = "true"
    env["RESET_CONFIG_ON_START"] = "true"
    if not env.get("WEBUI_SECRET_KEY"):
        env["WEBUI_SECRET_KEY"] = secrets.token_urlsafe(32)

    # Open WebUI OIDC configuration for the Keycloak sandbox realm.
    env["ENABLE_OAUTH"] = "true"
    env["OAUTH_CLIENT_ID"] = os.environ.get("OAUTH_CLIENT_ID", "openwebui")
    env["OAUTH_CLIENT_SECRET"] = os.environ.get("OAUTH_CLIENT_SECRET", "")
    env["OPENID_PROVIDER_URL"] = os.environ.get(
        "OPENID_PROVIDER_URL", "http://localhost:8082/realms/corp-kb/.well-known/openid-configuration"
    )
    env["OPENID_REDIRECT_URI"] = os.environ.get(
        "OPENID_REDIRECT_URI", "http://localhost:3100/oauth/oidc/callback"
    )
    env["OAUTH_PROVIDER_NAME"] = os.environ.get("OAUTH_PROVIDER_NAME", "Keycloak")
    env["OAUTH_SCOPES"] = os.environ.get("OAUTH_SCOPES", "openid email profile")
    env["ENABLE_OAUTH_SIGNUP"] = "true"
    env["OAUTH_MERGE_ACCOUNTS_BY_EMAIL"] = "true"

    if _openwebui_has_users():
        print("Open WebUI has existing users; authentication remains enabled.")
    else:
        print("Open WebUI has no users; first signup will create the admin account.")
    cmd = [
        str(venv_python),
        "-m",
        "uvicorn",
        "open_webui.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(OPENWEBUI_PORT),
    ]
    return _run_bg(cmd, env=env, cwd=backend_dir)


def _wait_for_services(timeout: float = 60.0) -> None:
    urls = {svc["name"]: f"http://127.0.0.1:{svc['port']}/health" for svc in SERVICES}
    remaining = dict(urls)
    deadline = time.time() + timeout
    while remaining and time.time() < deadline:
            for name, url in list(remaining.items()):
                try:
                    r = httpx.get(url, timeout=2)
                    if r.status_code == 200:
                        print(f"{name} is healthy at {url}")
                        del remaining[name]
                except httpx.HTTPError as exc:
                    print(f"Waiting for {name}: {exc}")
            if remaining:
                time.sleep(1)

    if remaining:
        raise RuntimeError(f"Services did not become healthy: {list(remaining)}")


def _stop_processes(processes: list[subprocess.Popen[Any]]) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def start_stack(openwebui: bool = True) -> list[subprocess.Popen[Any]]:
    _run(INFRA_COMMAND)
    _wait_for_postgres()
    _wait_for_keycloak()
    keycloak_cfg = _setup_keycloak()
    os.environ["KEYCLOAK_CLIENT_SECRET"] = keycloak_cfg["identity_client_secret"]
    os.environ["OAUTH_CLIENT_SECRET"] = keycloak_cfg["openwebui_client_secret"]

    for svc in SERVICES:
        if svc["migrations"]:
            _run_alembic(svc["migrations"])
    _seed_data()
    processes = _start_services()
    _wait_for_services()
    if openwebui:
        _reset_openwebui_users()
        owui = _start_openwebui()
        if owui is not None:
            processes.append(owui)
    print("\nLocal stack is running.")
    for svc in SERVICES:
        print(f"  {svc['name']:12} http://127.0.0.1:{svc['port']}")
    if openwebui:
        print(f"  {'openwebui':12} http://127.0.0.1:{OPENWEBUI_PORT}")
    print("\nPress Ctrl+C to stop.")
    return processes


def stop_stack() -> None:
    _run(INFRA_STOP_COMMAND)
    print("Infrastructure stopped.")


def main() -> int:
    parser = argparse.ArgumentParser(description="corp-ai-db local stack orchestrator")
    parser.add_argument(
        "--stop",
        action="store_true",
        help="stop infrastructure and exit without starting services",
    )
    parser.add_argument(
        "--no-openwebui",
        action="store_true",
        help="skip starting the Open WebUI frontend",
    )
    args = parser.parse_args()

    if args.stop:
        stop_stack()
        return 0

    processes: list[subprocess.Popen[Any]] = []

    def _shutdown(signum: int, _frame: Any) -> None:
        print("\nShutting down...")
        _stop_processes(processes)
        stop_stack()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        processes = start_stack(openwebui=not args.no_openwebui)
        while True:
            for proc in processes:
                ret = proc.poll()
                if ret is not None and ret != 0:
                    print(f"Service exited unexpectedly: {proc.args} -> {ret}")
                    _shutdown(0, None)
            time.sleep(1)
    except (RuntimeError, subprocess.CalledProcessError, OSError) as exc:
        print(f"Stack failed: {exc}")
        _stop_processes(processes)
        stop_stack()
        return 1


if __name__ == "__main__":
    sys.exit(main())
