# External Skills — 公式 Skill 利用方針

このファイルは anthropics/skills 公式 plugin marketplace から導入した Skill を一覧し、
proprietary plugin のライセンス同意状況・外部 LLM (Codex 等) への送信可否を記録する。

**現在の状態 (2026-05-07): 公式 plugin は未導入**

理由:
- CSDG は LLM 主導の文章生成プロジェクトであり、現時点で PDF / Office / Web testing の自動化ニーズがない
- 自前 Skill (python-standards, pydantic-patterns, prompt-engineering, test-standards) で当面のコーディング規約・テスト・プロンプト設計はカバー可能
- Codex 連携 (`/cross-review` 等) は導入済 (Phase 5 完了)

将来の検討候補 (必要が生じた時点で `/setup-marketplace` 相当を実施):

| Skill 名 | カテゴリ | 用途 | 外部 LLM への送信 |
|---|---|---|---|
| pdf | proprietary | PDF 生成・読み取り | **禁止** (proprietary) |
| docx | proprietary | Word ドキュメント | **禁止** (proprietary) |
| xlsx | proprietary | スプレッドシート | **禁止** (proprietary) |
| pptx | proprietary | プレゼンテーション | **禁止** (proprietary) |
| claude-api | Apache 2.0 | Anthropic SDK 開発 | 許可 |
| webapp-testing | Apache 2.0 | Playwright E2E | 許可 |
| skill-creator | Apache 2.0 | Skill 自動生成 | 許可 |
| mcp-builder | Apache 2.0 | MCP サーバー開発 | 許可 |

## ライセンス整合との関係

`scripts/secrets-filter.sh` および `.claude/hooks/secrets-pre-filter.sh` は、
proprietary plugin がカバーする拡張子 (`.pdf` / `.docx` / `.xlsx` / `.pptx`) を
**外部 LLM (Codex) への送信時に DENY する**。本ファイルが真実源となる。

将来 proprietary plugin を導入した場合:
1. このファイルの該当行に「外部 LLM への送信: 禁止」を維持
2. `scripts/secrets-filter.sh` の `PROPRIETARY_EXTS` 配列を更新
3. `.claude/hooks/secrets-pre-filter.sh` の同配列を更新
4. `/verify-setup` のライセンス整合検証 (Step 2.6) で集合差分を確認

新たな proprietary Skill が将来追加された場合も同様の手順で同期する。

## ライセンス同意ログ

(該当なし — 現時点で proprietary plugin 未導入)
