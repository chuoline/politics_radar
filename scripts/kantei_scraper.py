# scripts/kantei_scraper.py

import os
import sys
import re
import sqlite3
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────
# three_codes ディレクトリを import パスに追加
# ─────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))       # .../politics_lader/scripts
BASE_DIR = os.path.dirname(SCRIPT_DIR)                        # .../politics_lader
THREE_CODES_DIR = os.path.join(BASE_DIR, "three_codes")
if THREE_CODES_DIR not in sys.path:
    sys.path.append(THREE_CODES_DIR)

# ここから three_codes 内のモジュールを「単体」で import
from pm_rag_init import upsert_pm_term, insert_speech, insert_chunk
from pm_rag_metrics import insert_chunk_metrics

# ─────────────────────────────
# 定数・メタデータ
# ─────────────────────────────

STATEMENT_LIST_URL = "https://www.kantei.go.jp/jp/104/statement/index.html"

PM_TERM_ID = "TAKAICHI_104"
PM_NAME = "高市 早苗"
TERM_START_DATE = "2025-10-21"  # 高市内閣発足日（例）
TERM_NOTE = "第104代内閣総理大臣 第1次内閣"


# ─────────────────────────────
# テキスト整形
# ─────────────────────────────

def normalize_text(s: str) -> str:
    """全角スペースや余分な空白・空行をある程度そろえる"""

    # 全角スペース → 半角スペース
    s = s.replace("\u3000", " ")

    # 改行コードを統一
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.rstrip() for line in s.splitlines()]

    # 先頭・末尾の空行を削除
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def extract_body_from_statement_page(full_text: str) -> str:
    """
    官邸の演説ページから、本文部分だけをざっくり抜き出す。
    ルール：
      - 「１ 始めに」など、行頭が全角数字＋空白の行を本文開始とみなす
      - 見つからなければ全文を返す
    """
    # 改行統一
    full_text = full_text.replace("\r\n", "\n").replace("\r", "\n")

    # 「１ 始めに」などを探す（全角数字 / 半角数字 両方対応）
    m = re.search(r"^[０-９0-9]+[ 　]", full_text, flags=re.MULTILINE)

    if m:
        body = full_text[m.start():]
    else:
        body = full_text

    return normalize_text(body)


# ─────────────────────────────
# DB 既存チェック
# ─────────────────────────────

def get_db_path() -> str:
    """
    pm_speeches.db のパスを dashboard.py と同様に決定する。
    BASE_DIR / db / pm_speeches.db
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))  # .../politics_lader/scripts
    base_dir = os.path.dirname(script_dir)                   # .../politics_lader
    return os.path.join(base_dir, "db", "pm_speeches.db")


def speech_exists(source_url: str) -> bool:
    """同じ source_url の speech が既にあるか確認"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM speeches WHERE source_url = ? LIMIT 1", (source_url,))
    row = cur.fetchone()
    conn.close()
    return row is not None


# ─────────────────────────────
# 官邸一覧ページから対象URLを拾う
# ─────────────────────────────

def find_statement_urls(limit: int = 10) -> list[tuple[str, str]]:
    """
    statement/index.html から
    「所信表明演説」など首相発言らしいリンクを複数件拾う（最大 limit 件）。
    戻り値: [(タイトル, URL), ...]
    """
    resp = requests.get(STATEMENT_LIST_URL, timeout=10)
    resp.encoding = resp.apparent_encoding

    soup = BeautifulSoup(resp.text, "html.parser")

    items: list[tuple[str, str]] = []

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        # ★ フィルタ条件はあとでいくらでも調整できます
        if ("所信表明演説" in text) or ("内閣総理大臣" in text) or ("記者会見" in text):
            url = urljoin(STATEMENT_LIST_URL, a["href"])
            items.append((text, url))

    # URL 重複を除去しつつ、先頭から limit 件だけ返す
    dedup: list[tuple[str, str]] = []
    seen: set[str] = set()
    for title, url in items:
        if url in seen:
            continue
        seen.add(url)
        dedup.append((title, url))
        if len(dedup) >= limit:
            break

    if not dedup:
        raise RuntimeError("首相発言らしきリンクが一覧から見つかりませんでした。")

    return dedup



# ─────────────────────────────
# 詳細ページから DB への投入
# ─────────────────────────────

def parse_datetime_from_url(url: str) -> str:
    """
    URL から日付を推定する簡易版:
      例: https://www.kantei.go.jp/jp/104/statement/2025/1024shoshinhyomei.html
      → '2025-10-24 00:00'
    """
    path = urlparse(url).path
    # /jp/104/statement/2025/1024shoshinhyomei.html
    parts = path.split("/")
    # parts[-2] = '2025', parts[-1] = '1024shoshinhyomei.html'
    year = None
    month = None
    day = None

    for p in parts:
        if p.isdigit() and len(p) == 4:
            year = p
    # 末尾ファイル名から MMDD を抜き出す
    m = re.search(r"(\d{4})", parts[-1])
    if m:
        mmdd = m.group(1)
        month = mmdd[:2]
        day = mmdd[2:]

    if year and month and day:
        return f"{year}-{month}-{day} 00:00"
    else:
        # 失敗したら「今日の日付」でフォールバック
        return datetime.now().strftime("%Y-%m-%d 00:00")


def fetch_and_insert_speech(url: str) -> None:
    """指定URLの演説ページを取得し、DB に 1チャンクとして登録する"""

    if speech_exists(url):
        print(f"[SKIP] 既に登録済みのようです: {url}")
        return

    # 1. ページ取得
    resp = requests.get(url, timeout=15)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    # 2. タイトル
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)
    else:
        # 取得できなければ適当なフォールバック
        title = "首相演説（タイトル取得失敗）"

    # 3. ページ全体テキストから本文を抽出
    full_text = soup.get_text("\n")
    body_text = extract_body_from_statement_page(full_text)

    # 4. 任期情報（まだなければ upsert）
    upsert_pm_term(
        pm_term_id=PM_TERM_ID,
        pm_name=PM_NAME,
        term_start_date=TERM_START_DATE,
        term_end_date=None,
        note=TERM_NOTE,
    )

    # 5. speeches へ INSERT
    speech_datetime = parse_datetime_from_url(url)
    context = "演説・記者会見（自動取得）"

    speech_id = insert_speech(
        pm_term_id=PM_TERM_ID,
        pm_name=PM_NAME,
        dt_iso=speech_datetime,
        title=title,
        context=context,
        raw_text=body_text,
        source_url=url,
    )

    # 6. いまは「全文＝1チャンク」
    chunk_id = insert_chunk(
        speech_id=speech_id,
        text=body_text,
        order_in_speech=0,
    )

    # 7. メトリクス付与（カテゴリ・深さなどは insert_chunk_metrics にお任せ）
    insert_chunk_metrics(chunk_id)

    print("✅ 1本の演説を自動投入しました。")
    print("   URL      :", url)
    print("   speech_id:", speech_id)
    print("   chunk_id :", chunk_id)


# ─────────────────────────────
# エントリーポイント
# ─────────────────────────────

def main() -> None:
    print("=== 官邸サイトから首相発言を複数取得します ===")

    items = find_statement_urls(limit=10)

    for title, url in items:
        print("\n---")
        print("タイトル:", title)
        print("URL    :", url)
        fetch_and_insert_speech(url)


if __name__ == "__main__":
    main()