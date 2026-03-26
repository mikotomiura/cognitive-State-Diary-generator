# タスクリスト: log-analyzer 検出課題の修正

## Task 1: fatigue 範囲変更 (0.0〜1.0)
- [x] schemas.py: clamp_fatigue バリデータ分離
- [x] schemas.py: Field description 更新
- [x] schemas.py: docstring 更新
- [x] state_transition.py: fatigue 専用 clamp_lo
- [x] Prompt_StateUpdate.md: 範囲記述更新
- [x] architecture.md: 範囲記述更新
- [x] glossary.md: fatigue 定義更新
- [x] テスト更新 (test_schemas.py, test_state_transition.py)

## Task 2: unresolved_issue 更新促進
- [x] Prompt_StateUpdate.md: unresolved_issue 指示強化
- [x] Prompt_Critic.md: unresolved_issue 整合性チェック追加

## Task 3: emotional_plausibility 天井
- [x] deviation 分布分析
- [x] 対応方針決定: 方針C (fatigue変更後の観察) → 追加対応不要

## 検証
- [x] テスト全パス (290/290)
- [x] パイプライン再実行 (7/7Day完走, リトライ0回)
- [x] fatigue 範囲確認 (全Day ≥ 0.0)
- [x] unresolved_issue 更新確認 (Day 1,3,4,6 で設定/更新)
- [x] emotional_plausibility 改善確認 (スコア5: 1/7→3/7)
- [x] 結果レポート作成
