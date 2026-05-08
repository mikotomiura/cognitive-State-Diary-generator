# Tasklist — critic-verdict

## Step 0: 影響範囲調査

- [x] file-finder で `CriticScore` 参照箇所を列挙
- [x] impact-analyzer / file-finder で `judge()` の上流/下流を確認 (呼び出し元: `pipeline.py:1132` のみ)
- [x] log-analyzer で `output/generation_log.json` の Day 7 attempt 0 を再確認 (T=3 E=4 P=3 + reject_reason 確認、情報損失率 25%)
- [x] design.md の「未確定事項」を確定して埋める

## 実装

- [x] `csdg/schemas.py` — `Literal` import 追加 / `CriticScore.verdict: Literal["pass", "soft_fail", "hard_fail"]` 追加 (default=`"pass"`)
- [x] `csdg/schemas.py` — `derive_verdict` `model_validator(mode="after")` 追加 (既存 `check_reject_fields` の後に宣言)
- [x] `csdg/engine/critic.py` — `judge()` を `score.verdict == "pass"` に書き換え
- [x] `csdg/engine/pipeline.py` — soft_fail 時に `reject_reason` を Generator フィードバックに含める elif 追加
- [x] `prompts/Prompt_Critic.md` を確認 (変更不要 — 真実源は score + reject_reason、validator が verdict 再導出)

## テスト追加 / 更新

- [x] `tests/test_schemas.py::TestCriticScoreVerdict` — verdict pass / soft_fail / hard_fail / override / invalid / roundtrip / threshold (7 ケース)
- [x] `tests/test_critic.py::TestJudge::test_judge_rejects_soft_fail` — Day 7 attempt 0 相当ケースの judge() 動作
- [x] `tests/test_pipeline.py::TestSoftFailRetry` — soft_fail がリトライ起動 + reject_reason フィードバック流入 (2 ケース)

## ドキュメント

- [x] `docs/architecture.md` §3.3 (Critic) に verdict 概念を追記 (判定ロジック更新 + 表追加)

## 検証

- [x] `pytest tests/` 緑 (530 passed = 520 既存 + 10 新規)
- [x] `mypy csdg/ --strict` 通過 (16 source files)
- [x] `ruff check csdg/` 通過 / 該当ファイル `ruff format --check` 通過
- [x] tests/ の既存 ruff errors (25 件) は本タスク無関係 (pre-existing) と確認

## 仕上げ

- [x] requirement.md / design.md 最終化
- [x] decisions.md 作成 (D1: validator 順序 / D2: verdict 派生 / D3: フィードバック elif / D4: テストヘルパ非変更 / D5: Sprint スコープ厳密化 / D6: cross-review フィードバック採否 / D7: Codex 不在の経緯)
- [x] `/cross-review` 実施 — Codex は wrapper リグレッションで起動不可、Claude 単独レビュー fallback。Claude code-reviewer 7 件指摘のうち C-01 / W-01 / C-02 mitigation を反映 (3 件)
- [x] cross-review フィードバック反映後の再検証: 531 tests / mypy strict / ruff check すべて Green
- [x] コミットメッセージ準備 (`fix(critic): verdict フィールド導入で reject_reason 信号矛盾を解消`)
- [x] `/finish-task` でコミット実行 (d968b07)
