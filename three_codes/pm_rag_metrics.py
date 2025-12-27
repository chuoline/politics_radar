# pm_rag_metrics.py

from datetime import datetime, date
from typing import Tuple

from pm_rag_init import get_conn


def _parse_date(d: str) -> date:
    """
    'YYYY-MM-DD' または 'YYYY-MM-DD HH:MM' を date に変換
    """
    if len(d) >= 10:
        return datetime.strptime(d[:10], "%Y-%m-%d").date()
    raise ValueError(f"Invalid date string: {d!r}")


def calc_origin_phase(pm_term_id: str, date_str: str) -> float:
    """
    任期中の相対位置 (0.0〜1.0) を計算する。
    term_end_date が NULL の場合は「今日」までを任期とみなす。
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT term_start_date, term_end_date FROM pm_terms WHERE pm_term_id = ?",
        (pm_term_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"pm_term_id not found: {pm_term_id}")

    term_start_date, term_end_date = row
    start = _parse_date(term_start_date)
    end = _parse_date(term_end_date) if term_end_date else date.today()
    target = _parse_date(date_str)

    if target <= start:
        return 0.0
    if target >= end:
        return 1.0

    total_days = (end - start).days or 1
    pos_days = (target - start).days
    return max(0.0, min(1.0, pos_days / total_days))


# ------------------------------
# 仮のカテゴリ分類 ＋ 深さ推定
# （後で LLM に差し替え予定のダミー）
# ------------------------------

CATEGORIES = [
    "経済・財政",
    "外交・安全保障",
    "福祉・社会保障",
    "教育・子育て",
    "行政改革・政治改革",
    "災害・危機対応",
    "科学技術・デジタル",
    "その他",
]


def classify_chunk(text: str) -> Tuple[str, int]:
    """
    非常にラフなルールベース分類。
    将来 GPT などに置き換える前提の「仮版」です。

    戻り値:
        (category, depth_level)
    """
    t = text

    if any(k in t for k in ["景気", "物価", "GDP", "成長", "税", "財政"]):
        category = "経済・財政"
    elif any(k in t for k in ["防衛", "安全保障", "自衛隊", "同盟", "安保"]):
        category = "外交・安全保障"
    elif any(k in t for k in ["年金", "介護", "医療", "社会保障", "生活保護"]):
        category = "福祉・社会保障"
    elif any(k in t for k in ["教育", "学校", "子育て", "保育", "少子化"]):
        category = "教育・子育て"
    elif any(k in t for k in ["行政改革", "政治改革", "公務員", "行革", "統治機構"]):
        category = "行政改革・政治改革"
    elif any(k in t for k in ["地震", "災害", "台風", "被災", "復旧"]):
        category = "災害・危機対応"
    elif any(k in t for k in ["デジタル", "AI", "DX", "科学技術", "研究開発"]):
        category = "科学技術・デジタル"
    else:
        category = "その他"

    # 深さはとりあえず文字数ベースの簡易スコア
    length = len(text)
    if length < 80:
        depth = 0
    elif length < 250:
        depth = 1
    elif length < 600:
        depth = 2
    else:
        depth = 3

    return category, depth


def insert_chunk_metrics(chunk_id: int) -> None:
    """
    1つの chunk_id について:
      - chunks → speeches → pm_terms を JOIN し
      - category, depth_level, origin_phase を算出
      - chunk_metrics に UPSERT する
    """
    conn = get_conn()
    cur = conn.cursor()

    # chunk → speech 情報取得
    cur.execute(
        """
        SELECT c.text, s.pm_term_id, s.datetime
        FROM chunks AS c
        JOIN speeches AS s ON c.speech_id = s.id
        WHERE c.id = ?
        """,
        (chunk_id,),
    )
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"chunk not found: {chunk_id}")

    text, pm_term_id, dt_str = row
    date_str = dt_str[:10]  # 'YYYY-MM-DD'

    category, depth = classify_chunk(text)
    origin_phase = calc_origin_phase(pm_term_id, date_str)

    # chunk_metrics への UPSERT
    cur.execute(
        """
        INSERT INTO chunk_metrics(chunk_id, pm_term_id, date, category, depth_level, origin_phase)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(chunk_id) DO UPDATE SET
            pm_term_id   = excluded.pm_term_id,
            date         = excluded.date,
            category     = excluded.category,
            depth_level  = excluded.depth_level,
            origin_phase = excluded.origin_phase;
        """,
        (chunk_id, pm_term_id, date_str, category, depth, origin_phase),
    )

    conn.commit()
    conn.close()