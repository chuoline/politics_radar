# scripts/10_init_db.py
from scripts._db import connect

DDL = """
CREATE TABLE IF NOT EXISTS pm_terms (
    pm_term_id      TEXT PRIMARY KEY,
    pm_name         TEXT NOT NULL,
    term_start_date TEXT NOT NULL,
    term_end_date   TEXT,
    note            TEXT
);

CREATE TABLE IF NOT EXISTS speeches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pm_term_id  TEXT NOT NULL,
    pm_name     TEXT NOT NULL,
    dt          TEXT NOT NULL,
    title       TEXT,
    context     TEXT,
    raw_text    TEXT,
    source_url  TEXT,
    FOREIGN KEY (pm_term_id) REFERENCES pm_terms(pm_term_id)
);

CREATE TABLE IF NOT EXISTS chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    speech_id       INTEGER NOT NULL,
    text            TEXT NOT NULL,
    order_in_speech INTEGER NOT NULL,
    FOREIGN KEY (speech_id) REFERENCES speeches(id)
);

CREATE TABLE IF NOT EXISTS chunk_metrics (
    chunk_id     INTEGER PRIMARY KEY,
    pm_term_id   TEXT NOT NULL,
    date         TEXT NOT NULL,
    category     TEXT NOT NULL,
    depth_level  INTEGER NOT NULL,
    origin_phase REAL NOT NULL,
    created_at   TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (chunk_id) REFERENCES chunks(id)
);
"""

def main() -> None:
    with connect() as conn:
        conn.executescript(DDL)
    print("OK: init_db done")

if __name__ == "__main__":
    main()