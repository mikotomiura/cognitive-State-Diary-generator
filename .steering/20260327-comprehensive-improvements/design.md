# 設計: 全体精査に基づく包括的改善

## 実装アプローチ
5つの並行エージェントで独立した作業ストリームに分割:
1. actor.py 修正（Temperature Decay, 型安全性, prompt_loader共通化）
2. critic.py 修正（_load_prompt共通化, docstring, unresolved_issueチェック）
3. pipeline/memory/config 修正（デッドコード削除, サニタイズ, プロンプト外部化）
4. ドキュメント更新（architecture.md, glossary.md のメモリ構造記述）
5. テスト追加（critic veto, inverse_estimation, config プロパティ）

## 変更対象ファイル
| ファイル | 変更内容 |
|---|---|
| csdg/engine/actor.py | Temperature Decay修正, docstring, Any型コメント, _load_prompt共通化 |
| csdg/engine/critic.py | _load_prompt共通化, docstring追加, unresolved_issueチェック |
| csdg/engine/pipeline.py | デッドコード削除, revision_instructionサニタイズ, temperature引数 |
| csdg/engine/memory.py | プロンプト外部化, except Exception絞り込み |
| csdg/engine/critic_log.py | except Exception絞り込み |
| csdg/engine/prompt_loader.py | 新規: 共通プロンプト読み込み関数 |
| csdg/config.py | Field(exclude=True) |
| prompts/System_MemoryManager.md | 新規: メモリ管理システムプロンプト |
| pyproject.toml | 二重定義解消, バージョン上限追加 |
| docs/architecture.md | 2層メモリ構造の説明追加 |
| docs/glossary.md | メモリ関連用語追加 |

## 代替案と選定理由
- 各修正を個別コミットにする案 → 18件を個別にすると作業効率が著しく低下。論理的なグループでまとめる方針を採用
