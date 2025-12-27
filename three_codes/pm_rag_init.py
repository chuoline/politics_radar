# pm_rag_init.py (完全版)
import os
import sqlite3

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db")
DB_PATH = os.path.join(DB_DIR, "pm_speeches.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    db = get_conn()
    cur = db.cursor()

    cur.executescript(
        """
        DROP TABLE IF EXISTS pm_terms;
        DROP TABLE IF EXISTS speeches;
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS chunk_metrics;

        -- 任期テーブル
        CREATE TABLE pm_terms (
            pm_term_id      TEXT PRIMARY KEY,
            pm_name         TEXT NOT NULL,
            term_start_date TEXT NOT NULL,
            term_end_date   TEXT,
            note            TEXT
        );

        -- 演説テーブル
        CREATE TABLE speeches (
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

        -- チャンクテーブル
        CREATE TABLE chunks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            speech_id       INTEGER NOT NULL,
            text            TEXT NOT NULL,
            order_in_speech INTEGER NOT NULL,
            FOREIGN KEY (speech_id) REFERENCES speeches(id)
        );

        -- メトリクステーブル
        CREATE TABLE chunk_metrics (
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
    )

    db.commit()
    db.close()
    print("=== CREATED: pm_speeches.db ===")