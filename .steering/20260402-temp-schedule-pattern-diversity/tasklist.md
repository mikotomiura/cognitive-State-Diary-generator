# タスクリスト: 温度スケジュール精緻化 + パターン多様性向上

## 実装タスク
- [ ] H: config.py temperature_schedule を区分線形に変更
- [ ] I-1: pipeline.py _validate_structural_constraints に current_day 追加
- [ ] I-1: pipeline.py 呼び出し元で current_day を渡す
- [ ] I-2: actor.py generate_diary に prev_endings_text パラメータ追加
- [ ] I-2: actor.py _build_generator_prompt に prev_endings_text 注入コード追加
- [ ] I-2: pipeline.py から prev_endings_text を actor に渡す

## テストタスク
- [ ] test_config.py の温度スケジュールテスト更新
- [ ] test_pipeline.py のパターン上限テスト追加/更新

## 検証タスク
- [ ] mypy --strict 通過
- [ ] ruff check 通過
- [ ] pytest 全件 Pass
- [ ] パイプライン再実行 7/7 Pass
