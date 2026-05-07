# Agent Shared Context — CSDG

このファイルは Claude Code と Codex CLI の **両方** が参照する共通コンテキスト。
LLM 固有の指示は CLAUDE.md (Claude) / AGENTS.md (Codex) に分離している。

---

## プロジェクト概要

**CSDG (Cognitive-State Diary Generator)** — 体系的認知モデルに基づく AI キャラクター日記生成システム。
Actor-Critic 型の敵対的検証ループにより、7 日間のブログ日記を生成する。

- リポジトリ: https://github.com/mikotomiura/cognitive-State-Diary-generator
- 言語: **Python 3.11+**
- 主要フレームワーク: Pydantic v2, Anthropic API, Google Gemini API, matplotlib
- アーキテクチャ: **3-Phase Pipeline** (State Update → Content Generation → Critic Evaluation)

---

## ドキュメント体系

実装の前に必ず参照する:

| ドキュメント | パス | 目的 |
|---|---|---|
| 機能設計書 | `docs/functional-design.md` | 機能要件 / ユースケース |
| 技術設計書 | `docs/architecture.md` | システム構成 / データフロー / 技術選定 |
| リポジトリ構造定義書 | `docs/repository-structure.md` | ディレクトリ構成 / ファイル配置規約 |
| 開発ガイドライン | `docs/development-guidelines.md` | コーディング規約 / Git 運用 / テスト方針 |
| ユビキタス言語定義 | `docs/glossary.md` | プロジェクト固有の用語定義 |
| ERRE 設計文書 | `docs/erre-design.md` | ERRE フレームワークと CSDG の対応関係 |
| MVP 実装ワークフロー | `docs/mvp-implementation-workflow.md` | フェーズ別の実装手順・プロンプト |

公式 Skill の利用方針は @docs/external-skills.md を参照。

---

## 主要ディレクトリ

```
csdg/                   # アプリケーション本体
├── engine/             # Actor / Critic / LLM Client / Memory
├── pipeline.py         # 3-Phase オーケストレータ
├── schemas.py          # Pydantic v2 データモデル (型の中核)
├── config.py           # 設定 (EMOTION_SENSITIVITY 等)
└── main.py             # エントリポイント
prompts/                # 外部プロンプト (Markdown)
tests/                  # pytest テストスイート
output/                 # 生成日記・state_trajectory.png 出力先
docs/                   # 永続ドキュメント
.steering/              # タスクごとの作業ノート
```

詳細は `docs/repository-structure.md`。

---

## 開発の原則

1. **設計書ファーストで実装する** — コードを書く前に docs/ を読み、設計意図を理解する
2. **型安全性を最優先する** — Pydantic v2 モデルによる厳密な型定義を遵守。`Any` は最終手段
3. **テストなしのコミットは禁止** — 新機能・バグ修正には必ずテストを伴う
4. **プロンプトはコードに埋め込まない** — `prompts/` ディレクトリの外部 Markdown で管理
5. **Self-Healing を前提とする** — LLM 出力のパースエラーは発生する前提でフォールバックを実装

---

## よく使うコマンド

```bash
uv sync                                # 依存関係のインストール
pytest tests/ -v                       # テスト実行
pytest tests/ -v -m "not e2e"          # E2E を除外
mypy csdg/ --strict                    # 型チェック
ruff check csdg/                       # リンター
ruff format csdg/                      # フォーマッター
python -m csdg.main                    # パイプライン全実行
python -m csdg.main --day 4            # 特定 Day のみ
python -m csdg.main --dry-run          # API 呼び出しなし疎通確認
```

---

## テスト方針

- 単体テスト: `tests/test_<module>.py` 形式、AAA パターン
- E2E テスト: `@pytest.mark.e2e` でマーク (CI では `-m "not e2e"` で除外)
- フィクスチャ: `tests/conftest.py` に集約、scope を明示
- カバレッジ目標: 全体 80%、コアロジック (engine/) 90%
- LLM モック: `tests/conftest.py` の `mock_llm_response` フィクスチャを使用

詳細は `docs/development-guidelines.md` の「テスト方針」節。

---

## Git ワークフロー

- main ブランチに直接 push しない
- 機能開発: `feat/<area>-<short-desc>` (例: `feat/critic-discrimination`)
- バグ修正: `fix/<area>-<bug-id>` (例: `fix/best-of-n-last-write-wins`)
- プロンプト調整: `prompt/tune-<area>` (例: `prompt/tune-diary-quality`)
- コミットメッセージ: Conventional Commits ライク (`feat:` / `fix:` / `refactor:` / `docs:` / `chore:`)
- PR マージ: squash 推奨 (履歴の単位を「機能」に揃える)

詳細は `docs/development-guidelines.md` の「Git 運用」節。

---

## 禁止事項

- `schemas.py` のモデルを破壊的変更で無断更新しないこと (テスト/プロンプトとの一貫性が崩れる)
- プロンプトファイルに Python コードを埋め込まないこと
- `config.py` の感情感度係数 (`EMOTION_SENSITIVITY`) を根拠なく変更しないこと
- キャラクター設定 (ペルソナ) の禁則事項を無視した日記を生成しないこと
- `.steering/` の作業記録を省略しないこと

---

## 用語

主要用語は `docs/glossary.md` に集約。よく出る略語:
- **CSDG**: Cognitive-State Diary Generator (本プロジェクト)
- **CharacterState**: キャラクターの認知・感情状態 (frozen Pydantic モデル)
- **Critic Score**: 生成日記の品質評価スコア (Actor-Critic ループ)
- **Best-of-N**: 複数候補生成 → スコア最大の選択 (csdg/pipeline.py)
- **ERRE**: 設計フレームワーク (`docs/erre-design.md`)
