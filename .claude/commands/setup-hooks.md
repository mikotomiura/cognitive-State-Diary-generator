---
description: >
  Hook 群を .claude/hooks/ と settings.json に構築する。
  SessionStart Hook で動的情報を表示、Stop Hook で自己検証を強制、
  PostToolUse Hook で自動 lint を実行する。
  /setup-commands の完了後に実行する。
allowed-tools: Read, Write, Edit, Glob, Bash(mkdir *), Bash(chmod *), Bash(ls *)
---

# /setup-hooks — Hook 群構築コマンド

> Phase 6 of 7. Let's think step by step.
> Hook はエージェントループの外で決定論的に動作するスクリプト。
> 「人間が毎回チェックすべきこと」を Hook に任せる。

## 環境チェックブロック

### Check 1: 進捗ファイル

```bash
cat .steering/_setup-progress.md
```

Phase 5 完了を確認。

### Check 2: 既存設定の確認

```bash
ls -la .claude/
cat .claude/settings.json 2>/dev/null
```

既存の settings.json があれば内容を Read で確認。あれば追記モード、なければ新規作成モード。

### Check 3: コンテキスト予算

`/context` で 30% 以下を確認。

## 実行フロー

### Step 1: ユーザーへのヒアリング

このプロジェクトで使う Hook を決めるため、以下を質問:

1. lint ツール: 何を使っていますか?（ruff, eslint, prettier など）
2. format ツール: 何を使っていますか?
3. テストランナー: 何を使っていますか?
4. このプロジェクトで「セッション開始時に必ず確認したい情報」は何ですか?
5. 「実装完了時に必ず実行したいチェック」は何ですか?

回答を踏まえて以下の Hook を構築する。

### Step 2: ディレクトリ作成

```bash
mkdir -p .claude/hooks
```

### Step 3: SessionStart Hook の作成

CLAUDE.md にプロジェクトの動的情報を入れる代わりに、Hook で表示する。これにより CLAUDE.md をスリムに保てる。

`.claude/hooks/session-start.sh`:

```bash
#!/bin/bash
# Session start hook - プロジェクトの動的情報を表示

echo "════════════════════════════════════════"
echo "📍 Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"
echo "🔖 Last commit: $(git log -1 --oneline 2>/dev/null || echo 'N/A')"
echo "📝 Modified files: $(git status --short 2>/dev/null | wc -l | tr -d ' ')"

# 未対応 TODO の数
todo_count=$(grep -r "TODO\|FIXME\|HACK" src/ 2>/dev/null | wc -l | tr -d ' ')
echo "📋 Open TODOs: $todo_count"

# 進行中のタスク
current_tasks=$(ls -1 .steering/ 2>/dev/null | grep -E '^[0-9]{8}-' | tail -3)
if [ -n "$current_tasks" ]; then
    echo ""
    echo "🚧 Recent tasks in .steering/:"
    echo "$current_tasks" | sed 's/^/  - /'
fi

# プロジェクトタイプの検出
if [ -f "pyproject.toml" ]; then
    echo "🐍 Python project (pyproject.toml)"
fi
if [ -f "package.json" ]; then
    echo "📦 Node project (package.json)"
fi
if [ -f "Cargo.toml" ]; then
    echo "🦀 Rust project (Cargo.toml)"
fi

echo "════════════════════════════════════════"
```

権限を付与:

```bash
chmod +x .claude/hooks/session-start.sh
```

ユーザーに表示して承認を得る。プロジェクト固有の情報を追加したい場合は反映。

### Step 4: Stop Hook の設計

ターン終了時に自己検証を強制する。

settings.json に追加する設定（後で Step 7 でまとめて書く）:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "完了前に自己検証してください: (1) 変更したファイルのテストは実行したか? (2) 既存の規約から逸脱していないか? (3) 未対応の TODO コメントを残していないか? (4) エラーハンドリングは適切か? (5) `.steering/[現在のタスク]/tasklist.md` のチェックを更新したか? 問題があれば修正してから完了としてください。"
          }
        ]
      }
    ]
  }
}
```

### Step 5: PostToolUse Hook の設計

実装後の lint を自動化する。Step 1 で確認した lint ツールに応じて設定。

例（Python の場合）:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "ruff check --fix . 2>/dev/null || true"
          }
        ]
      },
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "ruff format . 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

例（TypeScript の場合）:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npx eslint --fix . 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

⚠️ **重要**: 必ず `2>/dev/null` でログを抑制する。これを忘れると 1 ターンで数万トークンを消費することがある。

ユーザーに確認:

> 「PostToolUse Hook で自動 lint を有効にしますか? 有効にすると Edit / Write のたびに lint が実行されます。トークンを消費する可能性があるため、必要なければ無効にできます。」

### Step 6: SessionStart Hook の登録

settings.json で SessionStart Hook を登録:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

### Step 7: settings.json の統合

すべての Hook 設定を 1 つの settings.json に統合する。

`.claude/settings.json` を作成または更新:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/session-start.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "完了前に自己検証してください: (1) 変更したファイルのテストは実行したか? (2) 既存の規約から逸脱していないか? (3) 未対応の TODO コメントを残していないか? (4) エラーハンドリングは適切か? (5) `.steering/[現在のタスク]/tasklist.md` のチェックを更新したか? 問題があれば修正してから完了としてください。"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "[ユーザーの環境に応じた lint コマンド] 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

既存の settings.json がある場合は、Edit ツールでマージする。上書きしない。

### Step 8: 動作テスト

ユーザーに以下を依頼:

> 「Hook が正しく設定されたかテストします。新しいセッションを開いて SessionStart Hook が動作することを確認してください。具体的には、`/clear` を実行した後にプロジェクト情報が表示されればOKです。」

### Step 9: Grill me ステップ

Hook 設定を批判的にレビュー:

> Hook 設定を批判的にレビューします:
> - SessionStart Hook の出力は簡潔か? (毎セッション表示されるため、長すぎると邪魔)
> - Stop Hook のプロンプトは具体的か?
> - PostToolUse Hook のコマンドは `2>/dev/null` でログを抑制しているか?
> - settings.json の構文は正しいか?
> - Hook がセッションを遅くする原因にならないか?

問題があれば修正。

### Step 10: 進捗ファイルの更新

`.steering/_setup-progress.md` の Phase 6 を完了マーク:

```markdown
- [x] **Phase 6: /setup-hooks** — Hook 群
  - 完了日時: [YYYY-MM-DD HH:MM]
  - 作成 Hook:
    - SessionStart: .claude/hooks/session-start.sh
    - Stop: 自己検証プロンプト
    - PostToolUse: 自動 lint ([ツール名])
  - settings.json: [新規作成 / 既存に追記]

### Hook → Command 参照
- SessionStart Hook → 全コマンドのセッション開始時に動作
- Stop Hook → 全コマンドのターン終了時に動作
- PostToolUse Hook → /add-feature, /fix-bug, /refactor 等の実装系で動作
```

### Step 11: 完了通知

```
Phase 6 完了です。

設定した Hook:
1. SessionStart Hook (.claude/hooks/session-start.sh)
   → セッション開始時にプロジェクト情報を表示
2. Stop Hook (settings.json)
   → ターン終了時に自己検証を強制
3. PostToolUse Hook (settings.json)
   → Edit/Write 後に自動 lint 実行

次のステップ:
1. `/clear` でセッションをリセット
2. SessionStart Hook が動作することを確認
3. `/setup-verify` を実行して全構築物の整合性チェック
```

## 完了条件

- [ ] `.claude/hooks/session-start.sh` が作成され、実行権限がある
- [ ] `.claude/settings.json` に 3 種類の Hook が設定されている
- [ ] PostToolUse Hook が `2>/dev/null` でログを抑制している
- [ ] Grill me ステップ実施済み
- [ ] 進捗ファイルが更新されている

## アンチパターン

- ❌ SessionStart Hook で大量の出力をする
- ❌ PostToolUse Hook でログを抑制しない（トークン消費爆発）
- ❌ Stop Hook を抽象的なプロンプトにする
- ❌ 既存の settings.json を上書きする
- ❌ Hook の動作テストを省略する
