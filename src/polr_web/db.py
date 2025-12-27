# src/polr_web/db.py
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]  # politics_radar/
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

def connect() -> sqlite3.Connection:
    db_path = get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn