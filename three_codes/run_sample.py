# run_sample.py

from pm_rag_init import init_db, upsert_pm_term, insert_speech, insert_chunk
from pm_rag_metrics import insert_chunk_metrics


def main() -> None:
    # 1. DB 初期化
    init_db()

    # 2. 任期情報（サンプル）
    pm_term_id = "104_SAMPLE"
    pm_name = "架空 太郎"

    upsert_pm_term(
        pm_term_id=pm_term_id,
        pm_name=pm_name,
        term_start_date="2025-01-01",  # 仮の就任日
        term_end_date=None,            # 現職とみなす
        note="サンプル任期",
    )

    # 3. 発言（全文1チャンク）を登録
    raw_text = (
        "本日は、我が国経済の現状と今後の財政運営についてご説明いたします。"
        "まず、物価高に苦しむ皆様への支援策として、政府として追加の対策を講じてまいります。"
    )

    speech_id = insert_speech(
        pm_term_id=pm_term_id,
        pm_name=pm_name,
        dt_iso="2025-02-01 15:00",
        title="経済政策に関する記者会見",
        context="記者会見",
        raw_text=raw_text,
        source_url="https://www.example.com/sample",
    )

    # 4. 「全文＝1チャンク」として登録
    chunk_id = insert_chunk(
        speech_id=speech_id,
        text=raw_text,
        order_in_speech=0,
    )

    # 5. チャンクにメタ情報を付与（カテゴリ／深さ／origin_phase）
    insert_chunk_metrics(chunk_id)

    print("サンプルデータ投入完了。pm_speeches.db をご確認ください。")


if __name__ == "__main__":
    main()