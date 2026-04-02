# 設計: 温度スケジュール精緻化 + パターン多様性向上

## 実装アプローチ

### H: 温度スケジュール
`temperature_schedule` プロパティの計算式を指数減衰からハードコードされた区分線形リストに置換。
`initial_temperature`, `temperature_final` フィールドは残し、新リストはプロパティ内で直接返す。

### I-1: パターン上限 Day 依存化
`_validate_structural_constraints()` に `current_day: int` パラメータを追加。
Day に応じた上限を計算し、既存のハードコード上限 (2, 3) を置換する。

### I-2: prev_endings_text 注入
`generate_diary()` と `_build_generator_prompt()` に `prev_endings_text` パラメータを追加。
`prev_openings_text` の注入コード (L648-657) と同様の形式で余韻テキストを注入。

## 変更対象ファイル
| ファイル | 変更内容 |
|---|---|
| `csdg/config.py` | temperature_schedule を区分線形に変更 |
| `csdg/engine/pipeline.py` | _validate_structural_constraints に current_day 追加、呼び出し元修正 |
| `csdg/engine/actor.py` | generate_diary / _build_generator_prompt に prev_endings_text 追加 |
| `tests/test_config.py` | 温度スケジュールテスト更新 |
| `tests/test_pipeline.py` | パターン上限テスト追加 |

## 代替案と選定理由
- 温度スケジュールを環境変数で設定可能にする案 → 過剰設計。固定リストで十分。
- パターン上限をプロンプトのみで制御する案 → LLMは上限を正確に守れないため、コード側での強制が必要。
