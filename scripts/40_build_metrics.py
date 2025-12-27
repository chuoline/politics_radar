# scripts/40_build_metrics.py
import argparse
from datetime import datetime, date
from typing import Tuple
from scripts._db import connect
import re

CATEGORIES = [
    "経済・財政",
    "治安・犯罪対策",   # ← 追加
    "外交・安全保障",
    "外交・首脳外交",
    "福祉・社会保障",
    "教育・子育て",
    "行政改革・政治改革",
    "国内政治・制度",
    "災害・危機対応",
    "科学技術・デジタル",
    "Q&A・記者質問",
    "構造・見出し",
    "その他",
]

def _parse_date(d: str) -> date:
    # accepts 'YYYY-MM-DD' or 'YYYY-MM-DD ...'
    if not d:
        return date.today()
    if len(d) >= 10:
        return datetime.strptime(d[:10], "%Y-%m-%d").date()
    raise ValueError(f"invalid date: {d}")

def calc_origin_phase(conn, pm_term_id: str, d_str: str) -> float:
    row = conn.execute(
        "SELECT term_start_date, term_end_date FROM pm_terms WHERE pm_term_id=?",
        (pm_term_id,),
    ).fetchone()
    if row is None:
        # 任期情報がない場合は 0.0 に倒す（復旧の安全側）
        return 0.0

    start = _parse_date(row["term_start_date"])
    end = _parse_date(row["term_end_date"]) if row["term_end_date"] else date.today()
    target = _parse_date(d_str)

    if target <= start:
        return 0.0
    if target >= end:
        return 1.0

    total_days = (end - start).days or 1
    pos_days = (target - start).days
    return pos_days / total_days

QNA_MARKERS = ["【質疑応答】", "（記者）", "（司会）"]

def classify_chunk(text: str) -> Tuple[str, int]:
    t = (text or "").strip()

    # 0) 構造・Q&A（最優先）
    if (
        any(k in t for k in QNA_MARKERS)
        or t.startswith("（記者")
    ):
        category = "Q&A・記者質問"

    # 発話者タグ： （高市総理）だけ、みたいな行
    elif re.fullmatch(r"（[^）]{1,12}）", t):
        category = "構造・見出し"

    # 質問者の名乗り（通信社/新聞/テレビ等）："…と申します"
    elif ("と申します" in t) and any(k in t for k in ["通信", "新聞", "テレビ", "放送", "共同", "時事", "NHK", "ロイター", "Reuters"]):
        category = "Q&A・記者質問"

    # 進行・受け答えの短文
    elif len(t) <= 30 and any(k in t for k in ["どうぞ", "大丈夫です", "お願いいたします", "ありがとうございます"]):
        category = "構造・見出し"


    # 0) 経済・財政（国内政治・制度より先に拾う：用語が明確）
    elif any(k in t for k in ["景気", "物価", "GDP", "成長", "税", "財政", "賃上げ", "投資", "金融"]):
        category = "経済・財政"


    # 1) 治安・犯罪対策（新設）
    elif any(k in t for k in [
        "治安", "犯罪", "テロ", "詐欺", "闇バイト", "ストーカー", "DV", "配偶者からの暴力",
        "性犯罪", "児童虐待", "被害者", "加害者", "暴力", "取り締まり", "検挙",
        "法規制", "規制強化"
    ]):
        category = "治安・犯罪対策"    


    # 2) 国内政治・制度（先に拾う：用語が明確）
    elif any(k in t for k in [
        "国会", "委員会", "法案", "改正", "制度", "政党", "選挙", "公職選挙法",
        "政治改革", "行政改革", "統治機構", "憲法", "内閣", "閣議", "与党", "野党"
    ]):
        category = "国内政治・制度"

    # 3) 災害・危機
    elif any(k in t for k in ["地震", "災害", "台風", "被災", "復旧", "危機", "感染症"]):
        category = "災害・危機対応"

    # 4) 福祉
    elif any(k in t for k in ["年金", "介護", "医療", "社会保障", "生活保護", "福祉"]):
        category = "福祉・社会保障"

    # 5) 教育
    elif any(k in t for k in ["教育", "学校", "子育て", "保育", "少子化", "奨学金"]):
        category = "教育・子育て"

    # 6) 科学技術・デジタル
    elif any(k in t for k in ["デジタル", "AI", "DX", "科学技術", "研究開発", "半導体"]):
        category = "科学技術・デジタル"

    # 7) 外交・安全保障（軍事寄り）
    elif any(k in t for k in ["防衛", "安全保障", "自衛隊", "安保", "抑止", "ミサイル", "侵略"]):
        category = "外交・安全保障"

    # 8) 外交・首脳外交（会談・国際会議寄り）
    elif any(k in t for k in [
        "首脳", "首脳会談", "会談", "会合", "国際会議", "サミット",
        "訪問", "外遊", "共同声明", "首相", "大統領", "国家主席", "外相",
        "ＡＰＥＣ", "APEC", "Ｇ７", "G7", "Ｇ２０", "G20", "国連", "UN",
        "ＡＳＥＡＮ", "ASEAN", "ＥＵ", "EU"
    ]):
        category = "外交・首脳外交"

    else:
        category = "その他"

    # 深さ（最後に一度だけ）
    length = len(t)
    if length < 80:
        depth = 0
    elif length < 250:
        depth = 1
    elif length < 600:
        depth = 2
    else:
        depth = 3

    return category, depth

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with connect() as conn:
        if args.rebuild:
            if args.dry_run:
                print("DRY-RUN: would delete chunk_metrics")
            else:
                conn.execute("DELETE FROM chunk_metrics;")
                conn.commit()
                print("OK: cleared chunk_metrics")

        rows = conn.execute(
            """
            SELECT
              c.id AS chunk_id,
              c.text AS chunk_text,
              s.pm_term_id AS pm_term_id,
              s.dt AS dt
            FROM chunks c
            JOIN speeches s ON s.id = c.speech_id
            ORDER BY c.id
            """
        ).fetchall()

        if not rows:
            raise SystemExit("ERROR: chunks is empty")

        n = 0
        for r in rows:
            n += 1
            pm_term_id = r["pm_term_id"]
            d_str = (r["dt"] or "")[:10]
            if not d_str:
                d_str = date.today().isoformat()

            cat, depth = classify_chunk(r["chunk_text"])
            phase = calc_origin_phase(conn, pm_term_id, d_str)

            if args.dry_run:
                continue

            conn.execute(
                """
                INSERT OR REPLACE INTO chunk_metrics
                (chunk_id, pm_term_id, date, category, depth_level, origin_phase)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (r["chunk_id"], pm_term_id, d_str, cat, depth, phase),
            )

        if not args.dry_run:
            conn.commit()

    print(f"OK: metrics built: {n} (dry_run={args.dry_run})")

if __name__ == "__main__":
    main()