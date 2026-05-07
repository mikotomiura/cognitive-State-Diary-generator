# Requirement — fix-codex-wrapper

## 親タスク・関連

- 直近タスク: `.steering/20260507-critic-verdict/decisions.md` D7 (Codex 不在の経緯)
- 影響を受ける機能: `/cross-review` コマンド、`codex-consult` / `codex-review` Skill、`cross-reviewer` agent

## 背景

PR #14 (`chore/codex-bridge-and-env-refactor`、本日 2026-05-07 マージ済み、commit `bbc75b3`) で `scripts/run-codex-{consult,review}.sh` が `codex exec` 起動時に **`-m gpt-5` を強制指定する形** に変わった。

しかし現環境は `codex login status` → `Logged in using ChatGPT` (ChatGPT サブスク認証)。`gpt-5` / `gpt-5-codex` / `gpt-5.1` はいずれも以下のエラーで拒否される:

```
ERROR: {"type":"error","status":400,"error":{"type":"invalid_request_error",
"message":"The 'gpt-5' model is not supported when using Codex with a ChatGPT account."}}
```

実証 (本セッションで確認):
- `echo "1+1" | codex exec -m gpt-5` → 失敗
- `echo "1+1" | codex exec` (model 未指定) → 成功 (11,950 tokens、`1 + 1 = 2`)

→ Codex CLI は ChatGPT 認証時にデフォルトモデルを **自動選択** するが、wrapper が `-m` を上書き指定するため不適切なモデルが渡される。`/cross-review` が起動できない (critic-verdict コミット時にも fallback 発生)。

## ゴール

- [ ] `scripts/run-codex-{consult,review}.sh` の `-m gpt-5` 強制を **環境変数 `CODEX_MODEL`** で切替可能にする
- [ ] `CODEX_MODEL=""` (空) の場合は `-m` 引数自体を渡さず CLI 自動選択に委ねる
- [ ] `CODEX_MODEL` 未設定時のデフォルト値は **`gpt-5`** を維持 (API key 認証ユーザーへの非破壊性)
- [ ] `.codex/config.toml` の `model = "gpt-5"` 行に運用メモコメント追記 (ChatGPT 認証時は env で空にせよ)
- [ ] `/cross-review` を再実行して Codex 起動成功を確認 (実 invocation ベース、ドライランではない)
- [ ] AGENTS.md L13-15 のモデル表に `CODEX_MODEL` env 変数の存在を 1 行追記

## 非ゴール

- `.codex/config.toml` の model 行自体の削除 (= AGENTS.md の "gpt-5 想定" 設計を変更しない)
- API key 認証への完全移行 (= OPENAI_API_KEY 設定はユーザー任意)
- `codex-rescue` Skill の wrapper 化 (現状直接 `codex` を呼ぶ設計、手付かず)
- `codex-consult` / `codex-review` の **モデル選択ロジック自体の改修** (consult=low / review=medium の reasoning_effort はそのまま)
- 新規モデル `gpt-5o` 等への切替検証

## 制約 / 前提条件

- 他のセッションの未コミット変更 6 modified が残っているが、本タスクで触るのは `scripts/run-codex-*.sh` と `.codex/config.toml` と `AGENTS.md` のみ
- `scripts/run-codex-*.sh` は bash で動作。POSIX 互換は不要 (`#!/bin/bash` 想定)
- 既存の機密フィルタ (`scripts/secrets-filter.sh`) と予算チェックは触らない
- shellcheck がパスすること (CSDG 開発ガイドライン)

## 完了条件 (Definition of Done)

- [ ] `CODEX_MODEL=""` で `echo "test" | scripts/run-codex-consult.sh` が `1` などのレスポンスを返す (実起動)
- [ ] `CODEX_MODEL=gpt-5` で同じ wrapper を起動 → 既存 (失敗) 挙動 (= 後方互換確認)
- [ ] `/cross-review` を直近の commit (d968b07) 範囲で実行 → Codex 起動成功 (Claude+Codex 両方の指摘が返る)
- [ ] `shellcheck scripts/run-codex-consult.sh scripts/run-codex-review.sh` 通過
- [ ] `.codex/config.toml` のコメント追記後、`/verify-setup` が緑 (Codex 疎通検証含む)
- [ ] AGENTS.md / 該当 docs の整合性確認
