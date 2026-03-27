# タスクリスト: prev_endings 注入による余韻反復防止

## 実装タスク
- [x] pipeline.py: _extract_ending ヘルパー追加
- [x] pipeline.py: prev_endings 蓄積ロジック追加（直近3件制限）
- [x] pipeline.py: run_single_day / generate_diary に prev_endings を受け渡し
- [x] actor.py: generate_diary / _build_generator_prompt に prev_endings パラメータ追加
- [x] actor.py: 「過去の余韻（使用済み）」セクションの構築ロジック
- [x] Prompt_Generator.md: {prev_endings} プレースホルダ追加

## テストタスク
- [x] TestExtractEnding: 複数段落 / 単一段落 / 空文字 / 末尾空白
- [x] TestPrevEndingsTracking: 受け渡し / 3件制限
- [x] TestPrevEndings: 注入あり / 注入なし

## 検証タスク
- [x] 321テスト全 Pass
- [x] mypy --strict クリーン
- [x] 2回の全Day実行で余韻の多様性確認
