---
name: codex-consult
description: >
  Codex CLI (gpt-5) を独立した設計相談相手として呼び出すための Skill。
  以下の状況で必須参照: 設計判断に迷った時、Claude 単独では視野が偏る恐れがある時、
  アーキテクチャの選択肢を比較したい時、複雑なバグの原因仮説を独立に検証したい時。
  read-only sandbox + low reasoning_effort で軽量に運用する。
  diff レビュー (codex-review) や rescue 実装 (codex-rescue) とは責務を分離する。
allowed-tools: Bash(scripts/run-codex-consult.sh:*), Read
---

# codex-consult — Codex を設計相談相手として使う

## このSkillが対象とするケース

- 「この設計でよいか」を Claude 単独で判断する前に、独立した第二意見が欲しい
- アーキテクチャの選択肢が 2-3 個あり、トレードオフを言語化したい
- 複雑なバグについて、Claude が立てた仮説を別の角度から検証したい
- プロンプトの構造設計を相談したい (CSDG では Actor/Critic 設計の見直しなど)

**対象外**: コード実装の依頼 (→ Claude 自身が書く / どうしても外部に頼みたいなら codex-rescue)、diff レビュー (→ codex-review)。

## 入力の制約 (重要)

Codex は **OpenAI の gpt-5 にプロンプトを送信する外部 LLM** であり、本プロジェクトの全ファイルを送るのは情報漏洩リスクがある。**送信内容は公開可能な最小抜粋に限定する**:

- ✅ 抽象的な設計の質問 ("Pydantic で discriminated union を扱うとき、validator のチェーン順序はどうあるべきか")
- ✅ 公開可能なコードスニペット (10-30 行程度)
- ✅ 一般的なパターン名・ライブラリ名
- ❌ API キー / 環境変数 / .env 内容
- ❌ プロジェクト固有のプロンプト全文 (`prompts/*.md`)
- ❌ ユーザーデータ・キャラクターペルソナの詳細
- ❌ proprietary 拡張子のファイル (`.pdf`, `.docx`, `.xlsx`, `.pptx`)

`scripts/run-codex-consult.sh` 内の `secrets-filter.sh` で機密パターン (API キー / private key / proprietary 拡張子) は自動 deny されるが、**フィルタは最終防衛線であり、入力時点で適切な抜粋を選ぶのが本来の責務**。

## 使い方

```bash
# 最小例 (引数渡し)
scripts/run-codex-consult.sh "Pydantic v2 で複数の field_validator がある時、実行順序の保証は?"

# stdin 経由 (長文)
cat <<'EOF' | scripts/run-codex-consult.sh
[抽象化された質問 + 公開可能スニペット]
EOF
```

## 出力の扱い

Codex の応答は **第二意見として参照する** が、以下を遵守:
- 応答内容を盲目的にコピペしない (バイアス・古い情報・本プロジェクト固有制約への無知の可能性)
- Claude 自身が再評価し、本プロジェクトの規約 (development-guidelines.md) と照合してから実装に反映
- 重要な設計判断は `.steering/[task]/decisions.md` に「Codex の意見も参照した」と明記

## 予算管理

`.codex/budget.json` の `daily_token_budget` (200000 token) を超えると wrapper が exit 3。
1 回あたりの目安: 500-3000 token (low reasoning なので軽い)。

## アンチパターン

- ❌ 「とりあえず Codex に聞く」 — Claude が最低 1 案考えてから比較相談に使う
- ❌ ファイル全文をそのまま流し込む — 抜粋する
- ❌ 機密情報・ユーザーデータを送る
- ❌ 同じ質問を再投する — 1 回の応答で十分なことが多い (予算節約)

## 関連 Skill

- `codex-review`: 完成した diff の独立レビュー (medium reasoning)
- `codex-rescue`: Claude が詰まった時の代替実装 (workspace-write + worktree 隔離)
