# 要件定義: 温度スケジュール精緻化 + パターン多様性向上

## 背景
v4安定版 (7/7 Pass, fallback 0) に対して、以下の2つの品質課題がログ分析から確認された:
- Day 4 (emotional_impact -0.8) のリトライ時、温度が急減衰し表現多様性が不足
- 冒頭「会話の残響」パターンが 3/7 Day で繰り返され、多様性目標 5/7 未達

## 実装内容

### H: 温度スケジュールの区分線形化
- `config.py` の `temperature_schedule` プロパティを指数減衰から区分線形に変更
- スケジュール: `[0.70, 0.60, 0.45, 0.30]`

### I-1: パターン上限の Day 依存化
- `pipeline.py` の `_validate_structural_constraints()` で:
  - 余韻パターン: Day 1-5 は各パターン1回まで、Day 6-7 は2回まで
  - 書き出しパターン: 同様に Day 依存化

### I-2: prev_endings_text のプロンプト注入
- `actor.py` で prev_endings_text を Generator プロンプトに注入
- prev_openings_text と同様の形式で過去の余韻テキストを明示

## 受け入れ条件
- [x] 温度スケジュールが `[0.70, 0.60, 0.45, 0.30]` になっている
- [ ] Day 1-5 でパターン上限が 1 に設定されている
- [ ] prev_endings_text がプロンプトに注入されている
- [ ] 既存テストが全件 Pass
- [ ] mypy --strict エラーなし
- [ ] パイプライン再実行で 7/7 Pass, fallback 0

## 影響範囲
- `csdg/config.py` — temperature_schedule プロパティ
- `csdg/engine/pipeline.py` — _validate_structural_constraints()
- `csdg/engine/actor.py` — generate_diary(), _build_generator_prompt()
