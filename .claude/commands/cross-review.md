# /cross-review — Codex 独立レビューを含む並列レビュー

> 重要 PR のマージ前、Claude 自身の自己バイアスを排除したい時に使う。
> `code-reviewer` (Claude/Opus) と `codex-review` (Codex/gpt-5) を並列起動し、
> 統合レポートを返す。

## 使い方

```
/cross-review                    # 現ブランチ vs main の差分
/cross-review HEAD~3..HEAD       # 直近 3 コミット
/cross-review #123               # PR #123 (要 gh CLI)
```

## 実行フロー

### Step 1: 引数解析

引数なし → デフォルト `main..HEAD`。
PR 番号が `#NNN` 形式 → `gh pr diff NNN` で diff 取得。
それ以外 → そのまま `git diff <arg>` の引数とみなす。

### Step 2: 3 段ガード (cross-reviewer agent 内)

`cross-reviewer` agent を Agent tool で起動。agent 内部で:
1. **diff 行数チェック** — `.codex/budget.json.diff_lines_threshold` (既定 800) を超えると拒否。ユーザーに分割提案。
2. **proprietary / 機密チェック** — `scripts/secrets-filter.sh` で fail-closed。
3. **日次予算チェック** — `.codex/budget.json.today.tokens_used >= daily_token_budget` なら codex 起動を skip し Claude 単独 fallback。

### Step 3: 並列レビュー

cross-reviewer agent が `code-reviewer` agent と `codex-review` Skill を並列起動。両者の結果を待つ。

### Step 4: 統合レポート出力

cross-reviewer agent が CRITICAL/HIGH/MEDIUM/LOW で重複排除した統合レポートを返す。
- `[両者一致]`: Claude と Codex の両方が指摘
- `[Claude]`: Claude のみ
- `[Codex]`: Codex のみ
- 「レビュアー間の見解差」セクション: 重大度評価が分かれた項目を列挙

### Step 5: ユーザーへの提示

統合レポートを以下の構造で返す:
- 上位指摘 (CRITICAL + HIGH 全件)
- MEDIUM / LOW は「全 N 件」の summary + 上位 3 件
- メタデータ (diff lines / codex tokens / ガード結果)

## アンチパターン

- ❌ 軽微な変更で起動する (Codex 予算の浪費)
- ❌ ガード失敗時にユーザーに通知せず黙って fallback する
- ❌ 統合せず Claude / Codex の結果を別個に長文で並べる (読み手に統合作業を強いる)
- ❌ codex の指摘を盲目的に採用する旨を含めない

## 制約

- 1 invocation あたりの想定トークン: 1500-5000 (medium reasoning)
- 1 日あたりの起動回数: 5-10 回程度を目安
- 800 行超の diff は拒否 → PR を機能単位で分割
- proprietary 拡張子 / 機密検出時は明示エラー

## 関連

- `cross-reviewer` agent: 並列オーケストレータ
- `code-reviewer` agent: Claude 単独レビュー (このコマンドの内部要素)
- `codex-review` Skill: Codex 独立レビュー (このコマンドの内部要素)
- `/review-changes` コマンド: 軽量の通常レビュー (Codex 不使用)
