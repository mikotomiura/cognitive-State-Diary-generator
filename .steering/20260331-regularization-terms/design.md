# 設計: 生成時正規化項の追加 (v6)

## 実装アプローチ

既存の `used_openings` / `used_structures` / `prev_endings` と同一のアーキテクチャパターンに従う:

1. Pipeline でパターン検出関数を定義
2. `PipelineRunner.run()` で追跡変数を初期化・蓄積
3. `run_single_day()` 経由で Actor に渡す
4. `Actor._build_generator_prompt()` でプロンプトセクションとして注入

## 変更対象ファイル

| ファイル | 変更内容 |
|---|---|
| `csdg/engine/pipeline.py` | `_detect_ending_pattern()`, `_count_theme_words()`, `_extract_rhetorical_questions()` 追加。定数定義。`run()`, `run_single_day()` に追跡変数追加 |
| `csdg/engine/actor.py` | `generate_diary()` シグネチャに3パラメータ追加。`_build_generator_prompt()` に3セクションの注入ロジック追加 |
| `tests/test_pipeline.py` | 3つの検出関数のユニットテスト |
| `tests/test_actor.py` | 新パラメータ注入のテスト |
| `docs/glossary.md` | 新用語追加 |

## 代替案と選定理由

| 代替案 | 却下理由 |
|---|---|
| Critic でスコアリング精密化 | v2-v4 で効果限定的と実証済み |
| Prompt_Generator.md に静的制約を追加 | Day 間の累計追跡ができない |
| 新しい config パラメータで閾値管理 | 定数が3つの関数内で完結するため、config に外出しする必要性が低い |
