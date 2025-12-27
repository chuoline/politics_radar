# politics_radar (MVP)

首相官邸等の発言テキストを **chunks** に分割し、各chunkに **カテゴリ/深さ/任期内位相(origin_phase)** を付与して分析・可視化するプロジェクトです。

- 母艦: スクリプト（Git管理）
- データ: 外付けSSD（DBや生成物）
- 実行: Python venv + .env

---

## 0. 前提

- macOS / zsh 想定
- Python 3.11+ 推奨（3.13でも可）
- 外付けSSDを `/Volumes/<SSD_NAME>/` にマウント済み

---

## 1. セットアップ

### 1) リポジトリ取得・移動
```bash
cd ~/projects/politics_radar

※ 現在は標準ライブラリのみで動作します。
外部ライブラリ導入後に requirements.txt を生成します。


---

## 2. 環境変数（.env）

このプロジェクトは **外付けSSD運用を前提** とします。  
実デバイス名・実パスは Git に含めません。

### 1) .env.example をコピー
```bash
cp .env.example .env


※ .env は Git管理しません
※ .env.example は 仕様書として Git 管理します
※ 現時点では外部ライブラリ不要です
※ Flask / scraping 導入時に requirements.txt を追加します

---

## 3. 設計判断の確認（あなたの理解は正しいか）

> タグを後回しにしたのは  
> 主題と従題の扱いを後回しにした、という理解で合っていますか？

**はい、完全に正しいです。**

- 現在：  
  **1 chunk = 1 主カテゴリ（分析軸）**
- 将来：  
  **chunk × 複数タグ（補助軸）**

このため、

- いま：  
  → **分析寄りUI（マトリクス・分布・時間軸）**
- あとで：  
  → **タグ追加しても壊れない**

という、**極めて健全な順序**になっています。

---

## 次の選択肢（ここから）

1. **READMEをこの形で確定**（おすすめ）  
2. Flask最小UI（カテゴリ×任期フェーズの2軸）を作る  
3. 官邸スクレイピング設計（再取得・差分更新）

あなたの宣言  
>「政治をしっかり考えてほしい青年に見せるUI」

を考えると、  
**次は 2 → 3 の順** が最も力強いです。

次は  
👉 *Flask最小UI（分析専用・編集不可）*  
を設計しますか？


2) venv 作成・依存導入
# venv 作成（未作成なら）
python -m venv .venv
source .venv/bin/activate

# pip 更新
python -m pip install -U pip

# 依存導入（Flask/UIを動かす最低限）
python -m pip install flask python-dotenv

3) .env 作成（最小構成）
cp .env.example .env
.env には 実デバイス名を含む実パスを入れます（Git管理しない）：
# --- DB（母艦DBで暫定運用する場合） ---
POLR_DB_PATH=/Users/tmyk0/projects/politics_radar/db/pm_speeches.db

# --- すでに外付けへ移した場合はこちら ---
# POLR_SSD_ROOT=/Volumes/SSPJ-UTC/politics_radar_data
# POLR_DB_PATH=/Volumes/SSPJ-UTC/politics_radar_data/db/pm_speeches.db

4) 動作確認（最初に doctor_env）
python -m scripts.doctor_env
	•	OK: DB exists が出れば次へ進めます。


5) パイプライン実行
python scripts/run_pipeline.py


6) Flask UI 起動（最短）
export FLASK_APP=src.polr_web.app:create_app
python -m flask run --debug
ブラウザで http://127.0.0.1:5000 を開きます。