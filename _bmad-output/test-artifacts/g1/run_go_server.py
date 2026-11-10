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
#   "uvicorn",
# ]
# ///

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import importlib

importlib.import_module("git-orchestrator.app.main")
for _original in list(sys.modules):
    if _original.startswith("git-orchestrator"):
        _aliased = _original.replace("git-orchestrator", "git_orchestrator")
        sys.modules[_aliased] = sys.modules[_original]

import uvicorn
from git_orchestrator.app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
