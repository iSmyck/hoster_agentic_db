"""Host-service launcher for local development.

Handles the ``git-orchestrator`` package name (which contains a hyphen) by
importing it under its real name and aliasing the loaded modules to
``git_orchestrator`` so uvicorn can resolve the conventional dotted path.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import uvicorn


def _alias_git_orchestrator() -> None:
    """Import git-orchestrator and mirror every module under git_orchestrator."""
    importlib.import_module("git-orchestrator.app.main")
    for original in list(sys.modules):
        if original.startswith("git-orchestrator"):
            aliased = original.replace("git-orchestrator", "git_orchestrator")
            sys.modules[aliased] = sys.modules[original]


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python src/run_service.py <service> <port>")
        print("Services: identity, session, go, retrieval, backup")
        return 1
    service = sys.argv[1]
    port = int(sys.argv[2])

    src_dir = str(Path(__file__).resolve().parent)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    if service == "go":
        _alias_git_orchestrator()
        module = sys.modules["git_orchestrator.app.main"]
    else:
        module = importlib.import_module(f"{service}.app.main")

    uvicorn.run(module.app, host="127.0.0.1", port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
