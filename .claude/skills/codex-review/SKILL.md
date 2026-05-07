---
name: codex-review
description: >
  Codex CLI (gpt-5.5) を独立したコードレビュアーとして呼び出し、git diff を独立評価する Skill。
  以下の状況で必須参照: 重要 PR のマージ前、Claude 自身が書いた diff へのバイアス排除が必要な時、
  /cross-review コマンドの内部から並列レビュアーとして起動される時。
  read-only sandbox + medium reasoning_effort で diff を評価し、CRITICAL/HIGH/MEDIUM/LOW で報告する。
  3 段ガード (行数 / proprietary / 予算) を必ず通過させること。
allowed-tools: Bash(scripts/run-codex-review.sh:*), Bash(git diff:*), Read
---

# codex-review — Codex による独立 diff レビュー

## このSkillが対象とするケース

- 重要 PR をマージする前の独立第二意見
- Claude が書いた diff の自己バイアス排除
- `/cross-review` コマンド内部からの並列レビュー要素

**対象外**: 設計の壁打ち (→ codex-consult)、コード実装 (→ codex-rescue)。

## 3 段ガード (実行前に必ず通す)

`scripts/run-codex-review.sh` 内で以下を順次確認:

### 1. diff 行数チェック
- `.codex/budget.json` の `diff_lines_threshold` (既定 800 行) を超える diff は **拒否 (exit 4)**
- 対応: PR を分割する / 局所的な diff を抽出してから再投する

### 2. 機密 / proprietary 拡張子チェック
- `secrets-filter.sh` が API キー / private key / `.pdf` / `.docx` / `.xlsx` / `.pptx` を検出すると **拒否 (exit 2)**
- 対応: 機密を除いた diff にする (例: `.env` の変更は除外)

### 3. 日次予算チェック
- `.codex/budget.json` の `daily_token_budget` (200000 token) を超過していると **拒否 (exit 3)**
- 対応: 翌日まで待つ / 予算ファイルを手動調整

## 使い方

```bash
# 主要な使い方 (git diff を流し込む)
git diff main..HEAD | scripts/run-codex-review.sh

# 既存の patch ファイル
cat my-patch.diff | scripts/run-codex-review.sh
```

wrapper が prompt 先頭に「独立第二レビュアーとして CRITICAL/HIGH/MEDIUM/LOW で報告せよ」を付与するので、呼び出し側は diff 本体だけを渡せばよい。

## 出力フォーマット

Codex は以下を返す:

```
CRITICAL:
  - ファイル:行番号 — 問題点 / 修正提案

HIGH:
  - ...

MEDIUM:
  - ...

LOW:
  - nitpick (任意)
```

Claude はこの出力を `code-reviewer` agent の結果と並列に並べ、重複排除した統合レポートを親に返す (`/cross-review` のフロー)。

## Atomic Budget Update

`token-report-stop.sh` (Stop hook) が冪等性キー `${date}:tokens=${used}:invs=${invocations}` で `.codex/budget.json` を更新する。**`flock` で排他制御** されているため、並列 codex 実行でも last-write-wins にはならない。

## アンチパターン

- ❌ 行数チェック前に diff を投げる (wrapper が拒否するが、呼び出し側で `wc -l` 確認するのが望ましい)
- ❌ 機密が含まれている可能性がある diff を投げる (まず `git diff -- ':!.env' ':!*.key'` で除外)
- ❌ 同じ diff を複数回レビューに投げる (予算浪費)
- ❌ Codex の指摘を盲目的に採用する (bias 排除のための独立意見であり、Claude が最終判断)

## 関連

- `cross-reviewer` agent: code-reviewer + codex-review を並列実行する オーケストレータ
- `/cross-review` command: ユーザー向けのトリガー
