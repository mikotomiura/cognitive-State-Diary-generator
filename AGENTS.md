# AGENTS.md — Codex CLI 固有指示 (CSDG)

**プロジェクト共通コンテキストは @docs/agent-shared.md を参照。** このファイルは Codex CLI 固有の運用ルールに限定する。

## Sandbox / Approval ポリシー

- 既定 sandbox: **read-only** (`.codex/config.toml` で設定)
- 既定 approval: **on-failure** (失敗時のみ確認)
- workspace-write が必要な時 (rescue 用途) は、**git worktree で隔離** + ユーザー明示承認 + `--sandbox workspace-write` を invocation 側で指定

## モデル / reasoning_effort

| 用途 | model | reasoning_effort | wrapper |
|---|---|---|---|
| 設計相談 (consult) | gpt-5 | low | `scripts/run-codex-consult.sh` |
| diff レビュー (review) | gpt-5 | medium | `scripts/run-codex-review.sh` |
| rescue 実装 | gpt-5 | high | (manual; worktree 隔離) |

直接 `codex exec` を呼ばず、必ず wrapper 経由で実行する。wrapper には機密フィルタ (`scripts/secrets-filter.sh`) と予算チェックが組み込まれている。

## 入力データの制約

外部 LLM (gpt-5) に送るため、以下は **絶対に送信しない**:
- API キー / 環境変数 / `.env` の内容
- ユーザーデータ / キャラクターペルソナ詳細
- proprietary 拡張子のファイル (`.pdf` / `.docx` / `.xlsx` / `.pptx`) — 詳細は @docs/external-skills.md
- プロンプトファイル (`prompts/*.md`) の全文 — 抜粋に留める

`scripts/secrets-filter.sh` が最終防衛線として fail-closed で動作する (exit 2)。

## 予算管理

- 日次トークン上限: `.codex/budget.json.daily_token_budget` (既定 200000)
- 1 invocation 上限: `per_invocation_max` (既定 40000)
- diff 行数しきい値: `diff_lines_threshold` (既定 800 行 — 超過時は `/cross-review` が拒否)
- 予算更新は `.claude/hooks/token-report-stop.sh` が flock 排他制御で実施

## 連携ポイント

- Skill: `codex-consult` (設計相談) / `codex-review` (diff レビュー) / `codex-rescue` (rescue 実装)
- Agent: `cross-reviewer` (Claude code-reviewer + Codex codex-review の並列オーケストレータ)
- Command: `/cross-review` (重要 PR 向けの並列レビュー)

## Rescue モード規約

Claude が同じ問題で 3 回以上ハマった時のみ rescue を検討する:
1. ユーザーに rescue 委譲の明示承認を取る (試した内容 + 期待成果物の説明)
2. `git worktree add .worktree-codex-rescue HEAD` で隔離
3. `--sandbox workspace-write -m gpt-5 -c model_reasoning_effort=high` で実行
4. 結果検証 (テスト / mypy / ruff) → cherry-pick or 破棄
5. 完了後 `git worktree remove .worktree-codex-rescue --force`

詳細は `.claude/skills/codex-rescue/SKILL.md`。
