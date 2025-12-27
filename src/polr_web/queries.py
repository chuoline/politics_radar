# src/polr_web/queries.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from .db import connect

THEMES = {
    "gx": {
        "label": "GX・エネルギー",
        "where": """
        (
          c.text like '%エネルギー%' or c.text like '%電力%' or c.text like '%原子力%' or
          c.text like '%再エネ%' or c.text like '%再生可能%' or c.text like '%GX%' or
          c.text like '%脱炭素%' or c.text like '%太陽光%' or c.text like '%風力%' or
          c.text like '%ペロブスカイト%'
        )
        """,
    },
    "local": {
        "label": "地方・人口",
        "where": """
        (
          c.text like '%地方%' or c.text like '%地方創生%' or c.text like '%人口減少%' or
          c.text like '%過疎%' or c.text like '%関係人口%' or c.text like '%二地域居住%' or
          c.text like '%農山漁村%' or c.text like '%中山間%' or c.text like '%農林水産%'
        )
        """,
    },
}

# def connect() -> sqlite3.Connection:
#     con = sqlite3.connect(get_db_path())
#     con.row_factory = sqlite3.Row
#     return con


def list_terms() -> List[Dict[str, Any]]:
    with connect() as con:
        rows = con.execute("""
            select pm_term_id, pm_name, term_start_date, term_end_date
            from pm_terms
            order by term_start_date
        """).fetchall()
    return [dict(r) for r in rows]

def matrix_summary(pm_term_id: Optional[str] = None) -> Dict[str, Any]:
    """
    returns:
      {
        "themes": [{"key":"gx","label":"..."}, ...],
        "rows": [
           {"category": "経済・財政", "cells": {"gx": {...}, "local": {...}}},
           ...
        ]
      }
    """
    themes = [{"key": k, "label": v["label"]} for k, v in THEMES.items()]

    with connect() as con:
        # category一覧（表示順は cnt desc）
        base_where = "1=1"
        params: List[Any] = []
        if pm_term_id:
            base_where += " and m.pm_term_id = ?"
            params.append(pm_term_id)

        cats = con.execute(f"""
            select m.category, count(*) as cnt
            from chunk_metrics m
            where {base_where}
            group by m.category
            order by cnt desc
        """, params).fetchall()

        rows_out = []
        for cr in cats:
            cat = cr["category"]
            cells = {}

            for tk, tv in THEMES.items():
                q = f"""
                select
                  count(*) as n,
                  avg(m.depth_level) as avg_depth,
                  avg(m.origin_phase) as avg_phase
                from chunks c
                join chunk_metrics m on m.chunk_id = c.id
                join speeches s on s.id = c.speech_id
                where m.category = ?
                  and {base_where}
                  and {tv["where"]}
                """
                p2 = [cat] + params
                r = con.execute(q, p2).fetchone()
                cells[tk] = {
                    "n": int(r["n"] or 0),
                    "avg_depth": float(r["avg_depth"] or 0.0),
                    "avg_phase": float(r["avg_phase"] or 0.0),
                }

            rows_out.append({"category": cat, "cells": cells, "total": int(cr["cnt"])})

    return {"themes": themes, "rows": rows_out}

def cell_items(category: str, theme_key: str, pm_term_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    if theme_key not in THEMES:
        raise ValueError("invalid theme_key")

    tw = THEMES[theme_key]["where"]

    base_where = "1=1"
    params: List[Any] = [category]
    if pm_term_id:
        base_where += " and m.pm_term_id = ?"
        params.append(pm_term_id)

    with connect() as con:
        rows = con.execute(f"""
            select
              c.id as chunk_id,
              s.dt as dt,
              s.pm_term_id as pm_term_id,
              m.category,
              m.depth_level,
              m.origin_phase,
              substr(c.text,1,120) as head
            from chunks c
            join chunk_metrics m on m.chunk_id = c.id
            join speeches s on s.id = c.speech_id
            where m.category = ?
              and {base_where}
              and {tw}
            order by s.dt, c.id
            limit ? offset ?
        """, params + [limit, offset]).fetchall()

    return [dict(r) for r in rows]

def chunk_detail(chunk_id: int) -> Dict[str, Any]:
    with connect() as con:
        row = con.execute("""
            select
              c.id as chunk_id,
              c.text,
              c.order_in_speech,
              s.id as speech_id,
              s.dt,
              s.pm_term_id,
              m.category,
              m.depth_level,
              m.origin_phase
            from chunks c
            join speeches s on s.id = c.speech_id
            join chunk_metrics m on m.chunk_id = c.id
            where c.id = ?
        """, (chunk_id,)).fetchone()
        if not row:
            raise KeyError("chunk not found")

        # 前後2つ（同speech内）
        speech_id = row["speech_id"]
        order_in_speech = row["order_in_speech"]
        neighbors = con.execute("""
            select c.id as chunk_id, substr(c.text,1,80) as head, c.order_in_speech
            from chunks c
            where c.speech_id = ?
              and c.order_in_speech between ? and ?
            order by c.order_in_speech
        """, (speech_id, max(1, order_in_speech - 2), order_in_speech + 2)).fetchall()

    return {"main": dict(row), "neighbors": [dict(r) for r in neighbors]}


PHASE_BINS = [
    (0.00, 0.20, "0-20%"),
    (0.20, 0.40, "20-40%"),
    (0.40, 0.60, "40-60%"),
    (0.60, 0.80, "60-80%"),
    (0.80, 1.01, "80-100%"),  # 1.0 を含めるため 1.01
]

def fetch_category_counts():
    with connect() as conn:
        rows = conn.execute("""
            SELECT category, COUNT(*) AS cnt
            FROM chunk_metrics
            GROUP BY category
            ORDER BY cnt DESC
        """).fetchall()
    return [dict(r) for r in rows]

def fetch_matrix_counts(exclude=("構造・見出し","Q&A・記者質問")):
    # phase_bin を Python 側で割り当て（SQLだけでも可能だが、まず安全に）
    with connect() as conn:
        rows = conn.execute("""
            SELECT category, origin_phase
            FROM chunk_metrics
            WHERE category NOT IN (?, ?)
        """, exclude).fetchall()

    # 集計
    matrix = {}  # matrix[category][bin_label] = n
    for r in rows:
        cat = r["category"]
        ph = float(r["origin_phase"] or 0.0)
        label = None
        for a,b,lbl in PHASE_BINS:
            if a <= ph < b:
                label = lbl
                break
        if label is None:
            label = "unknown"

        matrix.setdefault(cat, {lbl:0 for _,_,lbl in PHASE_BINS})
        matrix[cat][label] += 1

    return matrix, [lbl for _,_,lbl in PHASE_BINS]

