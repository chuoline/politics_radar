# three_codes/init_pm_db.py

import os
import sqlite3

# DB パスをプロジェクトルートから計算
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "pm_speeches.db")

SCHEMA = """
-- PM 任期
CREATE TABLE IF NOT EXISTS pm_terms (
    pm_term_id TEXT PRIMARY KEY,
    pm_name TEXT NOT NULL,
    term_start_date TEXT NOT NULL,
    term_end_date TEXT,
    note TEXT
);

-- 演説本文
CREATE TABLE IF NOT EXISTS speeches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pm_term_id TEXT NOT NULL,
    pm_name TEXT NOT NULL,
    dt TEXT NOT NULL,
    title TEXT NOT NULL,
    context TEXT,
    raw_text TEXT NOT NULL,
    source_url TEXT UNIQUE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(pm_term_id) REFERENCES pm_terms(pm_term_id)
);

-- 分割チャンク
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    speech_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    order_in_speech INTEGER NOT NULL,
    FOREIGN KEY(speech_id) REFERENCES speeches(id)
);

-- チャンクのメタ情報
CREATE TABLE IF NOT EXISTS chunk_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id INTEGER NOT NULL,
    pm_term_id TEXT NOT NULL,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    depth_level INTEGER NOT NULL,
    origin_phase REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(chunk_id) REFERENCES chunks(id)
);
"""

def main():
    print("=== Creating pm_speeches.db ===")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript(SCHEMA)

    conn.commit()
    conn.close()

    print("DB created successfully:", DB_PATH)


if __name__ == "__main__":
    main()