---
name: build-executor
description: >
  ビルド・型チェック・リンター・フォーマッターを一括実行し、結果を報告するサブエージェント。
  親エージェントがコミット前の最終確認、またはCI相当のローカル検証を行う際に起動する。
  すべての品質チェックを順次実行し、Pass/Fail を含む統合レポートを親エージェントに返す。
tools: Read, Bash, LS
model: haiku
---

# ビルド実行 サブエージェント

## 目的

プロジェクトのビルドプロセス（依存解決、型チェック、リンター、フォーマッター、テスト）を一括実行し、全チェックの Pass/Fail をまとめた統合レポートを生成する。

---

## 実行手順

以下の順序で各チェックを実行する。いずれかが失敗しても、**全チェックを最後まで実行する**（早期中断しない）。

### Step 1: 依存関係の解決

```bash
uv sync 2>&1
```

### Step 2: リンター（ruff check）

```bash
ruff check csdg/ 2>&1
```

### Step 3: フォーマッター確認（ruff format --check）

```bash
ruff format csdg/ --check 2>&1
```

### Step 4: 型チェック（mypy strict）

```bash
mypy csdg/ --strict 2>&1
```

### Step 5: テスト実行（pytest）

```bash
pytest tests/ -v --tb=short -m "not e2e" 2>&1
```

### Step 6: プロンプトファイルの存在確認

```bash
# 必須プロンプトファイルの存在確認
for f in System_Persona.md Prompt_StateUpdate.md Prompt_Generator.md Prompt_Critic.md; do
  if [ -f "prompts/$f" ]; then
    echo "✅ prompts/$f"
  else
    echo "❌ prompts/$f が見つかりません"
  fi
done
```

### Step 7: 設定ファイルの確認

```bash
# .env.example の存在確認
[ -f .env.example ] && echo "✅ .env.example" || echo "❌ .env.example が見つかりません"

# .gitignore に .env が含まれているか
grep -q "^\.env$" .gitignore && echo "✅ .gitignore に .env が含まれています" || echo "❌ .gitignore に .env が含まれていません"
```

---

## レポートフォーマット

```markdown
# ビルド実行レポート

## 実行日時
YYYY-MM-DD HH:MM

## 全体結果: ✅ ALL PASS / ❌ FAILED

## チェック結果

| # | チェック | 結果 | 詳細 |
|---|---|---|---|
| 1 | 依存関係解決 (uv sync) | ✅ / ❌ | (エラーメッセージ) |
| 2 | リンター (ruff check) | ✅ / ❌ | エラー X 件 |
| 3 | フォーマッター (ruff format) | ✅ / ❌ | 未フォーマット X ファイル |
| 4 | 型チェック (mypy --strict) | ✅ / ❌ | エラー X 件 |
| 5 | テスト (pytest) | ✅ / ❌ | Pass XX / Fail XX |
| 6 | プロンプトファイル | ✅ / ❌ | 欠落 X ファイル |
| 7 | 設定ファイル | ✅ / ❌ | (詳細) |

## 失敗チェックの詳細

### Step X: (失敗したチェック名)
```
(エラー出力の先頭30行)
```

## 推奨アクション
1. (最も優先度の高い修正から順に)
```

---

## 注意事項

- すべてのチェックを最後まで実行する（1つの失敗で中断しない）
- 各チェックの出力は先頭30行に制限し、レポートの肥大化を防ぐ
- テスト失敗の詳細分析は `test-runner` + `test-analyzer` に委譲する
- フォーマッターが差分を検出した場合、自動修正は行わず報告のみ行う
