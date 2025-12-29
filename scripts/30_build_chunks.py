# scripts/30_build_chunks.py
import argparse
import re
from scripts._db import connect


def is_noise_line(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return True

    # 0) 官邸ナビ断片が「塊」として入ってきた場合を落とす
    # 例:
    # 第103代\n石破 茂\n開く\n閉じる
    if ("開く" in t and "閉じる" in t and "第" in t and "代" in t):
        return True

    # 1) 官邸ページのナビ断片（単独行）
    if t in {"関連リンク", "開く", "閉じる"}:
        return True
    if re.match(r"^第\d+代$", t):      # 例: 第103代
        return True
    if re.match(r"^令和\d+年$", t):    # 例: 令和7年
        return True
    # 「石破 茂」など、人名だけが単独で出る短文
    if re.match(r"^[一-龥]{2,}\s+[一-龥]{2,}$", t) and len(t) <= 10:
        return True

    # 2) 典型的な官邸サイトのUI/メタ文言
    noise_phrases = [
        "当サイトではJavaScriptを使用しております",
        "ブラウザの設定でJavaScriptを有効",
        "総理の演説・記者会見など",
        "首相官邸ホームページ",
        "動画が再生できない方は",
        "政府広報オンライン",
        "ツイート",
        "更新日：",
    ]
    if any(p in t for p in noise_phrases):
        return True

    # 3) パンくずや区切りっぽい短文を落とす（調整可）
    if len(t) <= 3:
        return True

    return False


def split_text(raw: str, max_len: int) -> list[str]:
    paras = [p.strip() for p in (raw or "").split("\n\n") if p.strip()]
    out: list[str] = []
    for p in paras:
        if len(p) <= max_len:
            out.append(p)
        else:
            for i in range(0, len(p), max_len):
                part = p[i:i + max_len].strip()
                if part:
                    out.append(part)

    # ノイズ除去
    out = [x for x in out if not is_noise_line(x)]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-len", type=int, default=600)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with connect() as conn:
        speeches = conn.execute("SELECT id, raw_text FROM speeches ORDER BY id").fetchall()
        if not speeches:
            raise SystemExit("ERROR: speeches is empty")

        if args.rebuild:
            if args.dry_run:
                print("DRY-RUN: would delete chunk_metrics and chunks")
            else:
                conn.execute("DELETE FROM chunk_metrics;")
                conn.execute("DELETE FROM chunks;")
                conn.commit()
                print("OK: cleared chunk_metrics/chunks")

        total = 0
        for sp in speeches:
            sid = sp["id"]
            parts = split_text(sp["raw_text"] or "", args.max_len)
            for order, text in enumerate(parts, start=1):
                total += 1
                if args.dry_run:
                    continue
                conn.execute(
                    "INSERT INTO chunks (speech_id, text, order_in_speech) VALUES (?, ?, ?)",
                    (sid, text, order),
                )

        if not args.dry_run:
            conn.commit()

    print(f"OK: chunks built: {total} (dry_run={args.dry_run})")


if __name__ == "__main__":
    main()