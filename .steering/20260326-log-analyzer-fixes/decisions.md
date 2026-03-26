# 決定事項記録: log-analyzer 検出課題の修正

## [2026-03-26] Task 1: fatigue 範囲を 0.0〜1.0 に変更

- **背景:** log-analyzer が Day 6,7 で fatigue が負値になることを検出。疲労度に負値は意味的に不自然。
- **変更内容:**
  - schemas.py: clamp_fatigue バリデータを分離 (0.0〜1.0)
  - state_transition.py: fatigue 専用 clamp_lo=0.0
  - Prompt_StateUpdate.md: 範囲記述を更新
  - glossary.md, architecture.md: fatigue 範囲の記述を更新
  - test_schemas.py, test_state_transition.py: テストケース更新
- **結果:** 全7日で fatigue ≥ 0.0 を確認。Day 2 で fatigue=0.000 (下限到達) — 正常動作。

## [2026-03-26] Task 2: unresolved_issue 更新促進

- **背景:** 7日間 unresolved_issue が一度も更新されなかった。
- **変更内容:**
  - Prompt_StateUpdate.md: unresolved_issue の設定・維持・更新ルールを具体化
  - Prompt_Critic.md: unresolved_issue 整合性チェックを追加
- **結果:**
  - Day 1: 新規設定 ✅ (効率化の虚しさ)
  - Day 3: 更新 ✅ (問いの否定への怒り)
  - Day 4: 更新 ✅ (AI自動化への絶望)
  - Day 6: 更新 ✅ (自己評価の揺らぎ)
  - Day 2,5,7: 前日から維持 ✅

## [2026-03-26] Task 3: emotional_plausibility 天井 — 方針C採用

- **分析結果:**
  - fatigue 範囲変更後、emotional_plausibility: [5,5,4,4,5,4,4] (前回 [4,4,4,4,4,5,4])
  - スコア5が 1/7→3/7 に増加
  - 平均: 4.14→4.43 に改善
  - ユニーク値数は 2 で変わらないが、分布が改善
- **判定:** 方針C (fatigue 変更後の観察) で十分な改善が得られた。追加対応は不要。
