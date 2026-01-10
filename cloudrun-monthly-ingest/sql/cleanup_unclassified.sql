-- =========================================================
-- cleanup_unclassified.sql
--
-- 目的:
--   UNCLASSIFIED かつ 他テーマあり の行を、証跡を残して削除する
--
-- 前提:
--   - speech_themes_cleanup_log が存在（無ければこのSQLが作る）
--   - speech_themes のPKは (speech_id, theme)
--
-- 実行手順:
--   1) DRY RUN（件数確認）
--   2) 証跡ログへ退避（reason付き）
--   3) トランザクション内で削除
--   4) 検証（0件確認）
-- =========================================================

-- 0) ログ表が無い場合に作成（空で作る）
CREATE TABLE IF NOT EXISTS speech_themes_cleanup_log AS
SELECT
  now() AS cleaned_at,
  NULL::text AS reason,
  st.*
FROM speech_themes st
WHERE false;

-- 0-2) reason列が無い場合に追加
ALTER TABLE speech_themes_cleanup_log
ADD COLUMN IF NOT EXISTS reason text;

-- ---------------------------------------------------------
-- 1) DRY RUN: 削除対象件数（ここで必ず確認）
-- ---------------------------------------------------------
SELECT COUNT(*) AS will_delete
FROM speech_themes st
WHERE st.theme = 'UNCLASSIFIED'
  AND EXISTS (
    SELECT 1
    FROM speech_themes st2
    WHERE st2.speech_id = st.speech_id
      AND st2.theme <> 'UNCLASSIFIED'
  );

-- （任意）対象一覧を確認したい場合（タイトル付き）
SELECT st.speech_id, s.speech_date, s.title, st.method, st.created_at
FROM speech_themes st
JOIN speeches s ON s.id = st.speech_id
WHERE st.theme = 'UNCLASSIFIED'
  AND EXISTS (
    SELECT 1
    FROM speech_themes st2
    WHERE st2.speech_id = st.speech_id
      AND st2.theme <> 'UNCLASSIFIED'
  )
ORDER BY st.speech_id;

-- ---------------------------------------------------------
-- 2) ログへ退避（証跡）
-- ---------------------------------------------------------
INSERT INTO speech_themes_cleanup_log(
  cleaned_at, reason, speech_id, theme, method, rule_id, confidence, created_at
)
SELECT
  now(),
  'unclassified_with_others_cleanup',
  speech_id, theme, method, rule_id, confidence, created_at
FROM speech_themes st
WHERE st.theme = 'UNCLASSIFIED'
  AND EXISTS (
    SELECT 1 FROM speech_themes st2
    WHERE st2.speech_id = st.speech_id
      AND st2.theme <> 'UNCLASSIFIED'
  );

-- ---------------------------------------------------------
-- 3) 削除（トランザクション）
-- ---------------------------------------------------------
BEGIN;

DELETE FROM speech_themes st
WHERE st.theme = 'UNCLASSIFIED'
  AND EXISTS (
    SELECT 1
    FROM speech_themes st2
    WHERE st2.speech_id = st.speech_id
      AND st2.theme <> 'UNCLASSIFIED'
  );

-- ---------------------------------------------------------
-- 4) 検証（0件になっていること）
-- ---------------------------------------------------------
SELECT COUNT(*) AS unclassified_with_others_after
FROM speech_themes st
WHERE st.theme = 'UNCLASSIFIED'
  AND EXISTS (
    SELECT 1
    FROM speech_themes st2
    WHERE st2.speech_id = st.speech_id
      AND st2.theme <> 'UNCLASSIFIED'
  );

COMMIT;

-- ---------------------------------------------------------
-- 5) 実行ログ確認（直近分）
-- ---------------------------------------------------------
SELECT cleaned_at, reason, speech_id, theme, method, rule_id, created_at
FROM speech_themes_cleanup_log
ORDER BY cleaned_at DESC, speech_id
LIMIT 50;