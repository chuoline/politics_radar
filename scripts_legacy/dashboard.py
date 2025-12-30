# scripts_legacy/dashboard.py
# -*- coding: utf-8 -*-
"""
Politics Radar - Line (Timeline) MVP Dashboard (Improved)

Policy:
- This UI does NOT evaluate / score / rank political statements.
- It only visualizes structural summaries (timeline, category, depth, volume)
  and always provides access back to the original text/source.

Run:
  streamlit run scripts_legacy/dashboard.py

DB:
  - Use env var POLR_DB_PATH if set
  - Otherwise default to db/pm_speeches.db (project-relative)
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import streamlit as st


# -------------------------
# Config
# -------------------------

def resolve_db_path() -> str:
    p = os.environ.get("POLR_DB_PATH")
    if p:
        return p
    return str(Path("db") / "pm_speeches.db")


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def file_mtime_iso(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return "N/A"
    import datetime as _dt
    ts = p.stat().st_mtime
    return _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


# -------------------------
# Queries
# -------------------------

@st.cache_data(show_spinner=False)
def fetch_pm_names(db_path: str) -> list[str]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT pm_name FROM speeches ORDER BY pm_name"
        ).fetchall()
    return [r["pm_name"] for r in rows]


@st.cache_data(show_spinner=False)
def fetch_dt_range(db_path: str) -> Tuple[Optional[str], Optional[str], int]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT MIN(dt) AS min_dt, MAX(dt) AS max_dt, COUNT(*) AS n FROM speeches"
        ).fetchone()
    if not row:
        return None, None, 0
    return row["min_dt"], row["max_dt"], row["n"]


@st.cache_data(show_spinner=False)
def fetch_line_list(
    db_path: str,
    pm_name: Optional[str],
    from_dt: Optional[str],
    to_dt: Optional[str],
) -> pd.DataFrame:
    """
    Line (timeline) list:
      - speech-level records
      - category_mode (mode of chunk categories; ties concatenated, stable order)
      - depth_max (max depth among chunks in speech)
      - origin_phase_avg
      - volume_chars (raw_text length)
    """
    # NOTE:
    # - chunk_metrics joins chunks by chunk_id -> chunks.id
    # - chunks joins speeches by speech_id -> speeches.id
    # - category_mode is computed as "mode" by chunk counts, and ties are joined.
    # - To keep a stable display order and avoid SQLite DISTINCT+separator limitation,
    #   we aggregate ties via a correlated subquery ordering categories alphabetically.
    sql = """
    WITH cat_counts AS (
      SELECT
        c.speech_id,
        m.category,
        COUNT(*) AS n
      FROM chunks c
      JOIN chunk_metrics m ON m.chunk_id = c.id
      GROUP BY c.speech_id, m.category
    ),
    cat_mode AS (
      SELECT
        cc.speech_id,
        cc.category
      FROM cat_counts cc
      JOIN (
        SELECT speech_id, MAX(n) AS max_n
        FROM cat_counts
        GROUP BY speech_id
      ) mx
      ON mx.speech_id = cc.speech_id AND mx.max_n = cc.n
    )
    SELECT
      s.id AS speech_id,
      s.pm_term_id,
      s.pm_name,
      s.dt,
      COALESCE(s.title, '') AS title,
      COALESCE(s.context, '') AS context,
      COALESCE(s.source_url, '') AS source_url,
      LENGTH(COALESCE(s.raw_text,'')) AS volume_chars,
      MAX(m.depth_level) AS depth_max,
      AVG(m.origin_phase) AS origin_phase_avg,
      COALESCE((
        SELECT GROUP_CONCAT(category, ' / ')
        FROM (
          SELECT DISTINCT category
          FROM cat_mode
          WHERE speech_id = s.id
          ORDER BY category
        )
      ), '') AS category_mode
    FROM speeches s
    JOIN chunks c ON c.speech_id = s.id
    JOIN chunk_metrics m ON m.chunk_id = c.id
    WHERE 1=1
      AND (:pm_name IS NULL OR s.pm_name = :pm_name)
      AND (:from_dt IS NULL OR s.dt >= :from_dt)
      AND (:to_dt IS NULL OR s.dt <= :to_dt)
    GROUP BY
      s.id, s.pm_term_id, s.pm_name, s.dt, s.title, s.context, s.source_url
    ORDER BY s.dt DESC;
    """

    params: Dict[str, Any] = {
        "pm_name": pm_name,
        "from_dt": from_dt,
        "to_dt": to_dt,
    }

    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()

    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        return df

    # UI-friendly formatting
    df["origin_phase_avg"] = df["origin_phase_avg"].astype(float).round(3)
    df["volume_chars"] = df["volume_chars"].astype(int)
    df["depth_max"] = df["depth_max"].astype(int)

    # Helper column for date widgets & sorting/display
    # dt can be "YYYY-MM-DD HH:MM" etc. We parse leniently.
    df["dt_parsed"] = pd.to_datetime(df["dt"], errors="coerce")
    df["date_only"] = df["dt"].astype(str).str.slice(0, 10)  # "YYYY-MM-DD" part

    return df


@st.cache_data(show_spinner=False)
def fetch_speech_detail(db_path: str, speech_id: int) -> Dict[str, Any]:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
              id AS speech_id, pm_term_id, pm_name, dt,
              COALESCE(title,'') AS title,
              COALESCE(context,'') AS context,
              COALESCE(source_url,'') AS source_url,
              COALESCE(raw_text,'') AS raw_text
            FROM speeches
            WHERE id = ?
            """,
            (speech_id,),
        ).fetchone()
    return dict(row) if row else {}


# -------------------------
# UI
# -------------------------

st.set_page_config(page_title="Politics Radar (Line MVP)", layout="wide")

db_path = resolve_db_path()

st.title("Politics Radar：線（時系列一覧）MVP")

# Policy banner (non-evaluative declaration)
st.info(
    "本画面は、発言を評価・採点・優劣比較するものではありません。"
    "表示される指標（カテゴリ、深度、量、時系列）は、発言の構造を把握するための集約であり、"
    "解釈と判断は閲覧者自身に委ねられます。"
)

with st.expander("指標の定義（ポリシー固定）", expanded=False):
    st.markdown(
        """
- **Volume**：`raw_text` の文字数（量の指標であり、重要度や良否を意味しません）
- **Depth（depth_max）**：speech内チャンクの **最大深度**（優劣ではなく構造の要約です）
- **Category（category_mode）**：speech内チャンクで **最頻出のカテゴリ**（同率は `A / B` で併記）
- **Origin Phase（origin_phase_avg）**：任期内の相対位置（speech内チャンクの平均）
        """
    )

# DB status
min_dt, max_dt, n_speeches = fetch_dt_range(db_path)

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("Speeches", n_speeches)
with col_b:
    st.metric("DB path", db_path)
with col_c:
    st.metric("DB updated", file_mtime_iso(db_path))

st.divider()

# Filters
pm_names = fetch_pm_names(db_path)
fcol1, fcol2, fcol3 = st.columns([2, 2, 3])

with fcol1:
    pm_choice = st.selectbox(
        "首相（pm_name）",
        options=["(ALL)"] + pm_names,
        index=0,
    )
    pm_name = None if pm_choice == "(ALL)" else pm_choice

# Date range via date_input (works with dt like "YYYY-MM-DD HH:MM" because we compare strings)
# We convert picked dates to "YYYY-MM-DD 00:00" / "YYYY-MM-DD 23:59:59" strings.
import datetime as _dt

def _to_from_dt(d: Optional[_dt.date]) -> Optional[str]:
    if d is None:
        return None
    return f"{d.isoformat()} 00:00:00"

def _to_to_dt(d: Optional[_dt.date]) -> Optional[str]:
    if d is None:
        return None
    return f"{d.isoformat()} 23:59:59"

# Parse min/max for default selection (best-effort)
def _parse_date_prefix(dt_str: Optional[str]) -> Optional[_dt.date]:
    if not dt_str:
        return None
    try:
        return _dt.date.fromisoformat(str(dt_str)[:10])
    except Exception:
        return None

default_from = _parse_date_prefix(min_dt)
default_to = _parse_date_prefix(max_dt)

with fcol2:
    d_from = st.date_input("期間（from）", value=default_from)  # single date
with fcol3:
    d_to = st.date_input("期間（to）", value=default_to)

from_dt = _to_from_dt(d_from) if d_from else None
to_dt = _to_to_dt(d_to) if d_to else None

# Load list
df = fetch_line_list(db_path, pm_name=pm_name, from_dt=from_dt, to_dt=to_dt)

st.subheader("線：発言一覧（時系列）")

if df.empty:
    st.warning("該当するデータがありません。フィルタ条件を調整してください。")
    st.stop()

# 表示順（公式トグル）
order = st.radio(
    "表示順",
    options=["新しい順（DESC）", "古い順（ASC）"],
    horizontal=True,
    index=0,  # デフォルトは新しい順
)

# Search (title + context)
q = st.text_input("検索（title / context の部分一致）", value="").strip()
df_view = df.copy()

if q:
    hay_title = df_view["title"].fillna("")
    hay_ctx = df_view["context"].fillna("")
    mask = hay_title.str.contains(q, case=False, na=False) | hay_ctx.str.contains(q, case=False, na=False)
    df_view = df_view[mask]

# 安定ソート：dt_parsed → speech_id
ascending = (order == "古い順（ASC）")
df_view = df_view.sort_values(
    by=["dt_parsed", "speech_id"],
    ascending=[ascending, ascending],
    kind="mergesort",  # 安定ソート
)

st.caption(f"表示件数：{len(df_view)} / 全件：{len(df)}")

if df_view.empty:
    st.warning("検索条件に一致するデータがありません。検索語を調整してください。")
    st.stop()

display_cols = [
    "speech_id",
    "dt",
    "pm_name",
    "title",
    "category_mode",
    "volume_chars",
    "depth_max",
    "origin_phase_avg",
]

st.dataframe(
    df_view[display_cols],
    use_container_width=True,
    hide_index=True,
)

# Selection to show point (original)
st.subheader("点：原本（全文）")

# Better selector: show dt | pm_name | title
options = []
id_map: Dict[str, int] = {}

for _, r in df_view.iterrows():
    sid = int(r["speech_id"])
    label = f'{r["dt"]}｜{r["pm_name"]}｜{r["title"]}'
    options.append(label)
    id_map[label] = sid

selected_label = st.selectbox(
    "表示する発言を選択してください（dt｜pm｜title）",
    options=options,
    index=0,
)

selected_id = id_map[selected_label]
detail = fetch_speech_detail(db_path, selected_id)

if not detail:
    st.error("speech_id に対応する発言が見つかりませんでした。")
    st.stop()

dcol1, dcol2 = st.columns([3, 2])
with dcol1:
    st.markdown(f"**{detail.get('dt','')}｜{detail.get('pm_name','')}**")
    st.markdown(f"**{detail.get('title','(no title)')}**")
    if detail.get("context"):
        st.caption(detail["context"])

with dcol2:
    url = detail.get("source_url", "")
    if url:
        st.link_button("官邸ページ（原典）を開く", url)
    else:
        st.caption("source_url が未設定です。")

st.text_area(
    "原文（raw_text）",
    value=detail.get("raw_text", ""),
    height=420,
)