import sqlite3
from datetime import datetime

DB_PATH = "politics.db"

# ============================================================
# 1. DB 初期化（4テーブル作成）
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS pm_terms (
        pm_term_id      TEXT PRIMARY KEY,
        pm_name         TEXT NOT NULL,
        term_start_date TEXT NOT NULL,
        term_end_date   TEXT,
        note            TEXT
    );

    CREATE TABLE IF NOT EXISTS speeches (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        pm_term_id      TEXT NOT NULL,
        pm_name         TEXT NOT NULL,
        datetime        TEXT NOT NULL,
        title           TEXT NOT NULL,
        context         TEXT NOT NULL,
        raw_text        TEXT NOT NULL,
        source_url      TEXT NOT NULL,
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (pm_term_id) REFERENCES pm_terms(pm_term_id)
    );

    CREATE TABLE IF NOT EXISTS chunks (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        speech_id       INTEGER NOT NULL,
        order_in_speech INTEGER NOT NULL,
        text            TEXT NOT NULL,
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (speech_id) REFERENCES speeches(id)
    );

    CREATE TABLE IF NOT EXISTS chunk_metrics (
        chunk_id        INTEGER PRIMARY KEY,
        pm_term_id      TEXT NOT NULL,
        date            TEXT NOT NULL,
        category        TEXT NOT NULL,
        depth_level     INTEGER NOT NULL,
        origin_phase    REAL NOT NULL,
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (chunk_id) REFERENCES chunks(id),
        FOREIGN KEY (pm_term_id) REFERENCES pm_terms(pm_term_id)
    );
    """)

    conn.commit()
    conn.close()
    print("DB initialized.")


# ============================================================
# 2. origin_phase の計算
# ============================================================

def compute_origin_phase(date_str: str, term_start: str, term_end: str | None):
    """
    任期中のどの位置かを 0.0〜1.0 で返す。
    """
    d = datetime.fromisoformat(date_str)
    ts = datetime.fromisoformat(term_start)
    te = datetime.fromisoformat(term_end) if term_end else datetime.now()

    total = (te - ts).days
    progressed = (d - ts).days

    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, progressed / total))


# ============================================================
# 3. カテゴリ＋深さ（仮のルール）
#    ※本来は GPT に差し替え予定
# ============================================================

def dummy_classify(text: str):
    """
    テキスト内容から暫定カテゴリと depth を返す。
    後で LLM 呼び出しに置換予定。
    """
    if "経済" in text:
        return ("経済・財政", 2)
    if "外交" in text:
        return ("外交・安全保障", 2)
    return ("その他", 1)


# ============================================================
# 4. 発言（全文1チャンク）を DB に投入
# ============================================================

def insert_full_speech(pm_term_id, pm_name, term_start_date, term_end_date,
                       speech_title, speech_datetime, context, text, source_url):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- 任期情報を UPSERT ---
    cur.execute("""
        INSERT INTO pm_terms(pm_term_id, pm_name, term_start_date, term_end_date)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(pm_term_id) DO NOTHING;
    """, (pm_term_id, pm_name, term_start_date, term_end_date))

    # --- speeches テーブル ---
    cur.execute("""
        INSERT INTO speeches(pm_term_id, pm_name, datetime, title, context, raw_text, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (pm_term_id, pm_name, speech_datetime, speech_title, context, text, source_url))

    speech_id = cur.lastrowid

    # --- chunks（全文＝1チャンク） ---
    cur.execute("""
        INSERT INTO chunks(speech_id, order_in_speech, text)
        VALUES (?, ?, ?)
    """, (speech_id, 0, text))

    chunk_id = cur.lastrowid

    # --- Metrics 付与 ---
    category, depth = dummy_classify(text)
    date_only = speech_datetime.split(" ")[0]

    origin = compute_origin_phase(date_only, term_start_date, term_end_date)

    cur.execute("""
        INSERT INTO chunk_metrics(chunk_id, pm_term_id, date, category, depth_level, origin_phase)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (chunk_id, pm_term_id, date_only, category, depth, origin))

    conn.commit()
    conn.close()

    print(f"Inserted speech {speech_id} (chunk {chunk_id}).")


# ============================================================
# 実行デモ
# ============================================================

if __name__ == "__main__":
    init_db()

    insert_full_speech(
        pm_term_id      ="104_SAMPLE",
        pm_name         ="架空 太郎",
        term_start_date ="2024-12-01",
        term_end_date   =None,
        speech_title    ="就任後記者会見",
        speech_datetime ="2025-01-15 14:00",
        context         ="記者会見",
        text            ="経済政策を最優先に取り組みます。国民生活の安定が必要です。",
        source_url      ="https://example.com/fake_speech"
    )