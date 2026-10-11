"""Shared pytest config — load env from /app/frontend/.env and /app/backend/.env."""
import os
from pathlib import Path


def _load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env(Path("/app/frontend/.env"))
_load_env(Path("/app/backend/.env"))
