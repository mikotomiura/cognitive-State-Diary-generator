# Decisions — critic-verdict

実装途中で確定した重要な設計決定を記録する。

## D1: Pydantic v2 `model_validator(mode="after")` の宣言順依存に依拠

**決定**: 既存 `check_reject_fields` を **先**、新 `derive_verdict` を **後** に宣言する。

**根拠**: Pydantic v2 では同一 `mode="after"` の `@model_validator` 群はクラス内宣言順に実行される。`check_reject_fields` が先に走ることで、`score<3 + reject_reason 欠落` の既存 ValidationError 挙動を維持できる。`derive_verdict` は正規化済みインスタンスに対して verdict を確定する。

**代替**: validator 統合 (1 個の validator で reject 必須化 + verdict 導出) も可能だが、既存 `check_reject_fields` を変更すると schemas.py の破壊的変更に近づくため不採用。

## D2: verdict は **派生フィールド** とし、LLM 直出し値より validator の再導出を優先

**決定**: `derive_verdict` は instance.verdict を **常に上書き** する。LLM が `verdict: "pass"` を返しても、score と reject_reason が soft_fail を示せば自動的に soft_fail へ正規化される。

**根拠**:
- 真実源を **score + reject_reason** に一本化。LLM 出力との二重管理を避ける。
- `prompts/Prompt_Critic.md` を変更しなくても整合する (LLM が verdict を理解しなくても問題なし)。
- Structured Outputs (Anthropic API) スキーマには `verdict` が含まれるが (default 持ちの Optional)、validator が後段で確定するため LLM 値は事実上参考情報にすぎない。

## D3: `pipeline.py` のフィードバックは `revision_instruction → reject_reason` の elif フォールバック

**決定**: `revision_parts` 構築箇所で:
```python
if critic_score.revision_instruction:
    revision_parts.append(critic_score.revision_instruction)
elif critic_score.reject_reason:
    revision_parts.append(critic_score.reject_reason)
```
の elif 分岐を追加する。両方 append すると重複情報になりやすいため elif に留める。

**根拠**:
- `hard_fail` ケースは既存 validator が両方を必須化しており、elif の右辺には到達しない → 既存挙動完全維持
- `soft_fail` ケースは LLM が revision_instruction を空のまま reject_reason のみ populate するパターンが output/generation_log.json で観測される → reject_reason をフィードバックに乗せる

## D4: 既存テスト・ファクトリの破壊的変更を避ける

**決定**: `tests/test_pipeline.py:62-79` の `_make_pass_score()` / `_make_reject_score()` は **変更しない**。verdict は default + validator 自動導出のため、既存ファクトリで生成される CriticScore も自然に正しい verdict が付与される。

**根拠**: schemas.py の破壊的変更を避ける (CLAUDE.md 禁止事項) ため、テストヘルパも触らずに後方互換性を確保する。新規テストは別クラス (`TestCriticScoreVerdict`, `TestSoftFailRetry`) で追加。

## D5: Sprint スコープを A-CRITICAL-1 に厳密に限定

**決定**: 本タスクで Best-of-N 並列化 (A-HIGH-1) や Arc Plan (A-HIGH-2) には触れない。soft_fail を検出するだけ → 既存リトライ機構に委ねる。

**根拠**: improvement-plan.md の Sprint 区分に従う。A-HIGH-1 は別タスク (`/start-task` で別途切る) で、verdict + Best-of-N の組み合わせ (例: N 候補から hard_fail を除外、soft_fail 候補同士で交叉) を扱う。

## D6: cross-review フィードバックの採否 (2026-05-07 追記)

### 採用したフィードバック

- **C-01 (Claude code-reviewer)**: `derive_verdict` で `object.__setattr__` を使用 → frozen-safety の future-proofing
- **W-01 (Claude code-reviewer)**: `tests/test_schemas.py` に `test_check_reject_fields_runs_before_derive_verdict` を追加 → validator 宣言順の明示的回帰テスト
- **C-02 mitigation (部分採用)**: D3 の elif フォールバック設計を覆さず、`docs/architecture.md` に「soft_fail 時に revision_instruction=None ありうる」旨を追記

### 不採用としたフィードバック

- **C-02 完全採用**: `_integrate_scores` 内で revision_instruction を補填する案 → D3 と矛盾するため見送り。pipeline.py の elif fallback で集約する設計を維持
- **W-02**: `CriticLogEntry` に verdict フィールド追加 → スコープ外。verdict は score+reject_reason から導出可能、生ログ分析で十分
- **W-03**: kwarg 名前依存テストの脆さ → revision_instruction kwarg は `Actor.generate_diary` の契約。シグネチャ変更時はテスト失敗で検出すべき
- **I-01, I-02**: docstring スタイル / テスト DRY → 既存パターン整合 / 早すぎる抽象化

## D7: Codex (`/cross-review`) の独立第二意見が今回は不在

`scripts/run-codex-review.sh` が `-m gpt-5` を強制指定するが、現環境は `Logged in using ChatGPT` (ChatGPT サブスク認証) で、`gpt-5` 系モデルは ChatGPT 認証では利用不可 → Codex 起動失敗。

**Why**: PR #14 (chore/codex-bridge-and-env-refactor) で wrapper が `-m gpt-5` を強制する形に変わったが、ChatGPT 認証環境ではこの引数が拒否される。リグレッション。

**How to apply**: 本タスクとは無関係のインフラ問題のため、別タスク (`fix-codex-wrapper`) で wrapper を環境変数経由 (`CODEX_MODEL` 切替) に修正する予定。本タスクの cross-review は **Claude 単独レビュー fallback** で完了 (Claude code-reviewer による 7 件指摘のうち 3 件を採用反映)。

将来 cross-review を再起動する際は、wrapper 修正完了後に重要 PR (schemas.py 変更等) を対象に再実行すること。

## 観測メトリクス (実装後の確認用)

実装後、`output/generation_log.json` を再生成して以下を確認することを推奨:

- 旧来 retry_count 平均と soft_fail 検出後の retry_count 平均の比較
- soft_fail → 再試行で score が伸びる率 (改善信号が活きるか)
- API 呼び出し総数の増加幅 (コスト影響)

KPI 目標 (improvement-plan.md より):
- 30 日後: スコア 5 出現率 0% → 10%
- スコア 3 出現率 (cliff edge) 62% → 40%
