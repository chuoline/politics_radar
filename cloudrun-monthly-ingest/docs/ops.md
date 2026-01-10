✅ 手順書（運用メモ：事故防止用）

運用：UNCLASSIFIED 掃除（証跡付き）

目的
UNCLASSIFIED が残っているが、他テーマが既に付与されている speech_id について、UNCLASSIFIED のみを削除する。削除前に必ず証跡ログへ退避し、説明可能性を確保する。

対象定義（削除条件）
	•	speech_themes.theme = 'UNCLASSIFIED'
	•	かつ同一 speech_id に UNCLASSIFIED 以外のテーマが1つ以上存在

実行ファイル
	•	sql/cleanup_unclassified.sql

手順
	1.	DRY RUN（件数確認）
will_delete を必ず確認する。想定と異なる場合はここで中止する。
	2.	対象一覧確認（任意だが推奨）
タイトル付きの一覧を見て、人間が妥当性を確認する。
	3.	証跡ログへ退避
speech_themes_cleanup_log に cleaned_at と reason を付けて保存する。
	4.	削除（BEGIN〜COMMIT）
削除後に unclassified_with_others_after = 0 を確認する。0でなければ COMMIT せず中止する。
	5.	ログ確認
cleaned_at と reason で「いつ、なぜ」消したかを確認できる。

説明責任（最低限の言い方）
	•	「UNCLASSIFIED は初期状態の仮ラベルであり、他テーマが付いた後は情報価値が重複するため削除した」
	•	「削除前に全件ログへ退避し、復元・追跡可能な状態を維持している」