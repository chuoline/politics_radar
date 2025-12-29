# scripts/_db.py
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]  # politics_radar/
load_dotenv(dotenv_path=REPO_ROOT / ".env")      # ★探索しない

DEFAULT_DB_REL = REPO_ROOT / "db" / "pm_speeches.db"

def get_db_path() -> str:
    p = os.environ.get("POLR_DB_PATH")
    if p:
        return str(Path(p).expanduser())

    root = os.environ.get("POLR_SSD_ROOT")
    if root:
        return str(Path(root).expanduser() / "db" / "pm_speeches.db")

    return str(DEFAULT_DB_REL)

def ensure_parent_dir(db_path: Optional[str] = None) -> None:
    p = Path(db_path or get_db_path())
    p.parent.mkdir(parents=True, exist_ok=True)

def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    ensure_parent_dir(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn