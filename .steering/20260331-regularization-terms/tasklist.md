# タスクリスト: プロンプト注入メカニズム改善 (v7)

## 前回完了 (v6-tuned2)
- [x] pipeline.py: `_SCENE_MARKERS` から4語除外、12語追加
- [x] pipeline.py: `_detect_ending_pattern` に5パターン追加
- [x] Prompt_Generator.md: 「場面構造の絶対制限」静的ルール追記
- [x] test_pipeline.py: マーカー整合性・弁別力・余韻分類テスト追加

## v7 実装タスク
- [x] actor.py: 場面構造パターン全追跡 + 連続使用検出 (改善案1)
- [x] actor.py: 余韻パターンのホワイトリスト注入 (改善案2)
- [x] pipeline.py: `_ENDING_PATTERN_EXAMPLES` 定数追加 (改善案2)
- [x] actor.py: 書き出しパターン別カウント + 上限警告 (改善案3)
- [x] pipeline.py: `_validate_structural_constraints()` 追加 (改善案4)
- [x] pipeline.py: `run_single_day()` に構造バリデーション統合 (改善案4)
- [x] Prompt_Generator.md: `{critical_constraints}` プレースホルダ追加 (改善案5)
- [x] actor.py: critical_constraints 組み立てロジック追加 (改善案5)

## テストタスク
- [x] test_pipeline.py: `_validate_structural_constraints` テスト (8件)
- [x] test_actor.py: 注入ロジックテスト更新

## v7b 実装タスク
- [x] pipeline.py: `_OPENING_PATTERN_EXAMPLES` 定数追加 (改善案A)
- [x] actor.py: 書き出し注入をホワイトリスト+具体例方式に変更 (改善案A)
- [x] pipeline.py: 構造違反限定リトライ追加 (改善案B)
- [x] actor.py: 主題語のイベント文脈警告追加 (改善案C)

## 品質チェック
- [x] pytest tests/ -v (438 passed)
- [x] mypy csdg/ --strict (0 errors)
- [x] ruff check csdg/ (0 errors)
- [x] ruff format csdg/ --check (0 files)
