# CLAUDE.md — Claude Code 固有指示 (CSDG)

**プロジェクト共通コンテキストは @docs/agent-shared.md を参照。** このファイルは Claude Code 固有の運用ルールに限定する。

公式 Skill 利用方針は @docs/external-skills.md を参照。

---

## .steering — 構造化作業ノート

各作業セッションで `.steering/` に作業記録を残すこと。詳細は `.steering/README.md`。

### ディレクトリ構造

```
.steering/
├── _template/                # タスク用テンプレート (5 ファイル)
├── _setup-progress.md        # Claude Code 環境構築の進捗
├── _verify-report-*.md       # /verify-setup の出力
└── [YYYYMMDD]-[タスク名]/     # 実タスクの作業ノート
    ├── requirement.md
    ├── design.md
    ├── tasklist.md
    ├── blockers.md (任意)
    └── decisions.md (任意)
```

### 作業フロー

1. `/start-task` で `.steering/[YYYYMMDD]-[タスク名]/` 作成 + テンプレート展開
2. `requirement.md` → `design.md` → `tasklist.md` の順に埋める
3. 実装中、tasklist.md のチェックを進めながら作業
4. ブロッカー / 重要決定 → `blockers.md` / `decisions.md` 追記
5. `/finish-task` で最終化 + コミット

---

## Plan モードの使用基準

複雑な変更 (3 ファイル以上 / アーキテクチャ影響) では Plan モードに入って `ExitPlanMode` で承認を取る。
小修正 / 1 ファイル変更 / バグ修正は Plan モード不要 — 直接実装。

---

## モデル選択ルール

サブエージェントの model フロントマター指定:
- 軽量系 (test-runner, build-executor, file-finder): **haiku** (高速・軽量、Glob/Grep 中心)
- 情報収集系 (dependency-checker, impact-analyzer, log-analyzer): **sonnet** (構造解析・推論を伴う)
- レビュー系 (code-reviewer, test-analyzer, security-checker): **opus** (品質重視)
- オーケストレータ (cross-reviewer): **sonnet**

---

## コンテキスト管理

- 大量の検索 / 探索が必要な時は `Agent` (subagent_type=Explore) でメインコンテキストを節約
- ツール結果の重要情報は応答内に記録 (auto-compact 後も残るように)
- 不要な `cat` / `ls` の繰り返しは避ける (Read / Grep / Glob を使う)

---

## サブエージェント

`.claude/agents/` を参照。

| カテゴリ | エージェント | 用途 |
|---|---|---|
| レビュー | `code-reviewer` | コードレビュー (opus) |
| レビュー | `test-analyzer` | テスト結果の分析 (opus) |
| レビュー | `security-checker` | セキュリティチェック (opus) |
| レビュー | `cross-reviewer` | Claude + Codex 並列レビュー (sonnet) |
| 情報収集 | `impact-analyzer` | 変更影響範囲調査 |
| 情報収集 | `dependency-checker` | 依存関係確認 |
| 情報収集 | `file-finder` | 関連ファイル検索 |
| 実行 | `test-runner` | テスト実行 |
| 実行 | `build-executor` | ビルド実行 |
| 実行 | `log-analyzer` | ログ分析 |

---

## スラッシュコマンド

`.claude/commands/` を参照。

| コマンド | 用途 |
|---|---|
| `/start-task` | タスク開始・作業記録初期化 |
| `/implement feat\|fix\|refactor` | 実装ワークフロー (3 タイプ統合) |
| `/reimagine` | プラン段階で初回案を破棄し B 案と比較 (アンカリング排除) |
| `/review-changes` | 通常レビュー (Claude のみ、軽量) |
| `/cross-review` | 並列レビュー (Claude + Codex、重要 PR 向け) |
| `/smart-compact` | handoff.md 生成 + /compact / /clear 推奨 (長時間セッション向け) |
| `/finish-task` | タスク完了処理 (テスト・コミット) |
| `/run-tests` | テスト実行・分析 |
| `/update-docs` | ドキュメント更新 |
| `/add-scenario` | シナリオ (DailyEvent) 追加 |
| `/tune-prompt` | プロンプトチューニング |

---

## Skill

`.claude/skills/` を参照。

| Skill | 用途 |
|---|---|
| `python-standards` | Python コーディング規約 |
| `pydantic-patterns` | Pydantic v2 モデル設計 |
| `prompt-engineering` | LLM プロンプト設計の原則 |
| `test-standards` | テスト設計・実装の基準 |
| `codex-consult` | Codex を設計相談相手として呼ぶ |
| `codex-review` | Codex で diff を独立レビュー |
| `codex-rescue` | Codex に rescue 実装を委譲 |

<!-- cross-ref-ok: Codex 委譲時のフロー説明として正当な参照 -->
## Codex への委譲 (任意)

自分の実装に独立した第二意見が欲しい時、または同じ問題で 3 回以上詰まった時は Codex CLI への委譲を検討する:
- 軽量な設計相談: `codex-consult` Skill
- diff の独立レビュー: `/cross-review` コマンド
- rescue 実装: `codex-rescue` Skill (要ユーザー明示承認)

詳細な運用ルール (sandbox / approval / モデル選択) は @AGENTS.md を参照。
<!-- /cross-ref-ok -->

---

## 禁止事項

- `schemas.py` の破壊的変更を無断で行わないこと
- プロンプトファイルに Python コードを埋め込まないこと
- `.steering/` の作業記録を省略しないこと
- ハードコード値で `EMOTION_SENSITIVITY` を変更しないこと
- ペルソナの禁則事項を無視した日記を生成しないこと
