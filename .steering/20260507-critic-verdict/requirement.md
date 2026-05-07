# Requirement — critic-verdict

## 親レポート

- `.steering/20260507-system-strict-review/strict-review.md` (CRITICAL-1)
- `.steering/20260507-system-strict-review/improvement-plan.md` §3 A-CRITICAL-1

## 背景

CSDG の Critic Pass/Reject 判定に **信号矛盾 (情報損失バグ)** が存在する。

- `csdg/engine/critic.py:115` の `judge()` は `all(score >= 3)` で Pass 判定
- `csdg/schemas.py:183` の `model_validator` は `score < 3` のときのみ `reject_reason` 必須を強制
- → **score ≥ 3 でも `reject_reason` を populate することが Pydantic レベルで許可**

実例 (`output/generation_log.json` Day 7 attempt 0):
```
scores: T=3 E=4 P=3 (全て ≥ 3)
reject_reason: "...いくつかの問題があります..."
```

LLM-Judge が内部で「問題あり」を認識しても、Pipeline は数値のみ見て Pass 扱い。**品質改善の貴重な信号が捨てられており、これがスコア plateau (62% が score=3 の合格ぎり) の主要因の一つ**と推定される。

## ゴール

- [ ] `CriticScore` に `verdict: Literal["pass", "soft_fail", "hard_fail"]` を**新フィールドとして追加** (後方互換: デフォルト値あり)
- [ ] `model_validator` で verdict を自動導出 (score<3 → hard_fail / score≥3 + reject_reason → soft_fail / それ以外 → pass)
- [ ] `critic.py` の `judge()` を verdict 主導に書き換え (`verdict == "pass"` のみ Pass)
- [ ] Pipeline のリトライループで soft_fail 時に `reject_reason` を Generator のフィードバックに含める
- [ ] verdict 各ケース (pass / soft_fail / hard_fail) のテスト追加
- [ ] Day 7 attempt 0 相当のケース (score=3 + reject_reason) で `verdict == "soft_fail"` を確認するテスト

## 非ゴール

- Best-of-N 並列化 (A-HIGH-1) — 別タスク
- Arc Plan (A-HIGH-2) — 別タスク
- Critic を診断器化 (A-HIGH-3) — 別タスク
- 既存 `CriticScore` フィールドの破壊的変更 — **明示的に禁止**
- `reject_reason` の必須化や型変更
- `EMOTION_SENSITIVITY` の変更

## 制約 / 前提条件

- **CLAUDE.md 禁止事項**: `schemas.py` の破壊的変更を行わない (新フィールド追加 + デフォルト値で後方互換)
- 既存の 520 tests がすべて緑のまま
- mypy --strict / ruff check / ruff format 通過
- 触る対象: `csdg/schemas.py`, `csdg/engine/critic.py`, `csdg/engine/pipeline.py`, `tests/test_schemas.py`, `tests/test_critic.py`, `tests/test_pipeline.py`
- Pydantic v2 の `model_validator` の order に注意 (既存 `check_reject_fields` と新 `derive_verdict` の順序)

## 完了条件 (Definition of Done)

- [ ] 既存 520 tests + 新規追加 tests がすべて緑
- [ ] verdict フィールドのテスト追加 (pass / soft_fail / hard_fail 各ケース)
- [ ] Day 7 attempt 0 相当ケースで `verdict == "soft_fail"` が出ることを確認するテスト
- [ ] mypy csdg/ --strict 通過
- [ ] ruff check csdg/ / ruff format --check csdg/ 通過
- [ ] docs/architecture.md の §3.3 (Critic) に verdict 概念を追記
- [ ] CHANGELOG エントリ (該当する場合)
- [ ] tasklist.md のチェックがすべて埋まっている
