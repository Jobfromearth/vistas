"""Snapshot location resolution, shared by the server and the build pipeline."""

from __future__ import annotations

import os
from pathlib import Path

DB_PATH_ENV = "VISTAS_DB"
DEFAULT_DB_PATH = Path.home() / ".vistas" / "snapshot.db"


def default_db_path() -> Path:
    env = os.environ.get(DB_PATH_ENV)
    return Path(env) if env else DEFAULT_DB_PATH
