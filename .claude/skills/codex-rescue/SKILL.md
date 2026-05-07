---
name: codex-rescue
description: >
  Codex CLI (gpt-5.5) を rescue 実装担当として呼び出すための Skill。Claude 自身が複数回試行しても
  解決できなかった実装課題を、git worktree 隔離環境で Codex に委譲する。
  以下の状況で必須参照: Claude が同じバグで 3 回以上ハマっている時、視点を変えるしかない時、
  ただし依頼前にユーザーから明示承認を得ること。workspace-write + 隔離 worktree のため、
  メインのワーキングツリーを汚さない。high reasoning_effort で慎重に実装させる。
allowed-tools: Bash(git worktree:*), Bash(scripts/run-codex-rescue.sh:*), Bash(git diff:*), Read
---

# codex-rescue — Codex による rescue 実装

## このSkillが対象とするケース

Claude が 3 回以上同じ問題で詰まり、視点を変える必要がある時のみ。**通常の実装には使わない**。
- 例: 複雑な型制約のリファクタで何度も mypy エラーを循環している
- 例: テストの失敗原因がどうしても特定できず、別の角度からのアプローチが必要

**対象外**: 通常実装 (→ Claude 自身)、設計相談 (→ codex-consult)、レビュー (→ codex-review)。

## 重要: 起動前にユーザー承認を取る

このSkillは **書き込み権限を持つ Codex を起動する** ため、起動前に必ずユーザーへ:
1. なぜ Codex に rescue を委譲するのか (試した内容 / 詰まったポイント)
2. 期待する成果物 (どのファイルが変更される予定か)
3. 隔離 worktree のパス (例: `.worktree-codex-rescue/`)
を提示し、明示承認を取る。

## 隔離 worktree の構築

```bash
# 1. 隔離環境を作る (メインの working tree を汚さない)
git worktree add .worktree-codex-rescue HEAD

# 2. Codex に rescue を依頼 (workspace-write、high reasoning)
cd .worktree-codex-rescue && codex exec \
  --sandbox workspace-write \
  -m gpt-5.5 \
  -c model_reasoning_effort=high \
  "[詳細な依頼文 + 試した内容 + 期待する出力]"

# 3. Claude が結果を検証
cd .worktree-codex-rescue && git diff HEAD

# 4. 採否判断 → メインに cherry-pick or 破棄
```

`scripts/run-codex-rescue.sh` は本 Skill の範囲外で、必要時に Phase 5 拡張で追加する想定 (現状は手動)。

## 採用判断のチェックリスト

Codex の出力をメインに取り込む前に Claude が確認:
- [ ] テストが緑か (`pytest tests/ -v`)
- [ ] mypy / ruff 通過するか
- [ ] CSDG 規約に違反していないか (development-guidelines.md)
- [ ] 不要なコメント / TODO / 過剰な error handling が混入していないか
- [ ] プロンプトファイルにコードを埋め込んでいないか
- [ ] schemas.py を破壊的変更していないか

問題があれば cherry-pick せず、worktree を `git worktree remove .worktree-codex-rescue --force` で破棄。

## 入力の制約

`codex-consult` と同様、**送信内容は公開可能な最小抜粋に限定**。worktree 内のファイルは codex の sandbox から見えるが、ユーザーデータや機密 (.env 等) を持ち込まない。

## 予算

high reasoning は token 消費が大きい (1 invocation で 5000-20000 token)。
`.codex/budget.json` の per_invocation_max (40000) と daily_token_budget (200000) を圧迫しないよう、依頼は短く具体的に。

## アンチパターン

- ❌ ユーザー承認なしに起動
- ❌ メインの working tree で直接 codex を走らせる (隔離せよ)
- ❌ Codex の出力を検証せずにマージ
- ❌ 「Claude が詰まった」が浅い試行段階 (3 回以上ハマってから検討)
- ❌ 完了後に worktree を残しっぱなし

## 関連

- `codex-consult`: 設計の壁打ち (実装委譲しない、軽量)
- `codex-review`: read-only レビュー (書き込まない)
