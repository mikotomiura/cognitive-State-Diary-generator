# Claude Code 環境構築 検証レポート

検証日時: 2026-05-08 12:11 JST
検証方法: `/verify-setup` (commands_setup version, 10 段階仕様)

## 総合判定

**⚠️ WARNINGS** — クリティカル/ハイは無し。LOW のみ 5 件で運用上の影響は無い。

## 構成サマリ

- **Phase 5 (Codex Bridge)**: ✅ 完了 (AGENTS.md / .codex/ 両方存在)
- **Phase 2 (Marketplace)**: ⚠️ skip 状態 (公式 plugin 未導入、空テンプレ生成済)
- **Codex 疎通**: ✅ PASS (exit 0、13,124 tokens 消費、応答正常)
- **AGENTS↔CLAUDE 同期**: ✅ leakage 0 (両方向)
- **ライセンス整合**: ✅ secrets-filter / secrets-pre-filter ともに 4 拡張子全カバー

## 各フェーズの状態

### Phase 1: docs ✅
すべての必須 5 ファイル + 補助 4 ファイル (erre-design.md, mvp-implementation-workflow.md, agent-shared.md, external-skills.md) が存在。

### Phase 2: Marketplace ⚠️ SKIPPED (意図的)
- `docs/external-skills.md`: ✅ 存在 (43 行、proprietary 4 + Apache 4 のテンプレ表)
- 導入済 plugin: 0 (CSDG 用途では PDF/Office/Web testing 不要と判断)
- proprietary 同意ログ: N/A
- 取り残しなし

### Phase 3: CLAUDE.md / AGENTS.md / agent-shared.md ✅
| ファイル | 行数 | 上限 | `@docs/agent-shared.md` 参照 | 必須セクション |
|---|---|---|---|---|
| CLAUDE.md | 133 | 150 | 1 | ✅ Plan mode / モデル選択 / .steering / Codex 委譲 |
| AGENTS.md | 55 | 80 | 1 | ✅ Sandbox / Approval / モデル / 入力制約 / 予算 / Rescue |
| docs/agent-shared.md | 126 | 200 | (`@docs/external-skills.md` を 1 回参照) | ✅ プロジェクト概要 / アーキ / ディレクトリ / テスト / Git |

責務分離 (Step 2.5):
- CLAUDE.md の Codex 系 keyword leakage: **0** (cross-ref-ok marker 適用後)
- AGENTS.md の Claude 系 keyword leakage: **0**
- 共通 keyword (プロジェクト概要 / アーキ / ディレクトリ / テスト方針 / git ワークフロー) の重複: **0**

### Phase 4: Skills ✅
- 自前 Skill: 4 (python-standards, pydantic-patterns, prompt-engineering, test-standards)
- Codex Skill: 3 (codex-consult, codex-review, codex-rescue)
- 全 7 Skill が `name` / `description` / `allowed-tools` の 3 frontmatter を保持
- 自前 Skill は 3 ファイル構成 (SKILL.md + 2 補足)
- 動的 Skill: 中期 TODO (進捗ファイル既出)
- 公式 Skill 重複: なし

### Phase 5: Codex Bridge ✅
- `.codex/config.toml`: ✅ (model=gpt-5.5, sandbox=read-only, approval=on-failure)
- `.codex/budget.json`: ✅ JSON 構造正常 (daily 200k, per-invocation 40k, diff threshold 800)
- `scripts/secrets-filter.sh` / `run-codex-consult.sh` / `run-codex-review.sh`: ✅ 全実行可能
- 3 codex skills (consult/review/rescue): ✅
- **疎通テスト**: ✅ PASS — `gpt-5.5` 応答正常、13,124 tokens

### Phase 6: Agents ✅
全 10 エージェント存在。モデル割当が CLAUDE.md 規約に整合:

| Agent | model | 規約 | 整合 |
|---|---|---|---|
| build-executor | haiku | haiku (実行系) | ✅ |
| code-reviewer | opus | opus (レビュー系) | ✅ |
| cross-reviewer | sonnet | sonnet (オーケストレータ) | ✅ |
| dependency-checker | sonnet | sonnet (情報収集) | ✅ |
| **file-finder** | **haiku** | sonnet (情報収集系) | ⚠️ 不一致 |
| impact-analyzer | sonnet | sonnet | ✅ |
| log-analyzer | sonnet | sonnet | ✅ |
| security-checker | opus | opus | ✅ |
| test-analyzer | opus | opus | ✅ |
| test-runner | haiku | haiku | ✅ |

cross-reviewer の tools: `Bash, Read, Grep, Glob, LS` — Bash 直接権限あり (`Bash(codex *)` の制限は declare レベルでは未記述)。実運用では wrapper 経由が agent description で要求されている。

### Phase 7: Commands ⚠️
spec の基本 8 コマンドのうち実装状況:
- ✅ /start-task / /review-changes / /finish-task / /cross-review
- 🔀 /add-feature, /fix-bug, /refactor → **`/implement` に統合済 (意図的、c142b74)**
- ❌ /reimagine, /smart-compact — 未実装 (LOW, 進捗ファイル既出)
- 追加: /run-tests, /update-docs, /add-scenario, /tune-prompt, /implement, /review

/cross-review の 3 段ガード (line 26: 行数 / 27: proprietary / 28: 予算): ✅ 実装済

### Phase 8: Hooks ✅
3 層構成 + Codex 第 4 層 + 情報表示層、計 8 hook ファイルすべて実行権限付き。

| 層 | hook | 検証結果 |
|---|---|---|
| 情報表示 | session-start.sh | ✅ |
| Preflight | preflight.sh | ✅ exit 0 厳守 |
| Guard | pre-edit-steering.sh | ✅ `[guard] PASS` 出力 |
| Codex Guard | codex-budget-guard.sh | ✅ `*codex*` 早期 exit |
| Codex Guard | secrets-pre-filter.sh | ✅ 同上、proprietary 4 拡張子 DENY |
| Report | post-fmt.sh | ✅ `--check` 先判定 + `[fmt] applied` |
| Report | stop-check.sh | ✅ 出力 `>/dev/null 2>&1` 抑制 + `[stop] WARN` |
| Codex Report | token-report-stop.sh | ✅ 冪等性キー + flock |

settings 関連:
- ⚠️ **`.claude/settings.json` が存在しない、`.claude/settings.local.json` のみ**
- 機能上問題なし: 全 8 hook が `"type": "command"` で正しく登録済
- spec の名称と差異あり (LOW)

### Phase 9: verify-setup ✅
本検証実行、レポート保存。

## 相互参照の整合性

| 検証項目 | 結果 |
|---|---|
| CLAUDE.md → @docs/agent-shared.md | ✅ 1 reference |
| AGENTS.md → @docs/agent-shared.md | ✅ 1 reference |
| docs/agent-shared.md → @docs/external-skills.md | ✅ 1 reference |
| AGENTS↔CLAUDE 同期 | ✅ leakage 0 |
| ライセンス整合 (external-skills ↔ secrets-filter ↔ secrets-pre-filter) | ✅ 4 拡張子完全カバー |
| Codex 疎通 | ✅ PASS |
| Hook ファイル ↔ settings.local.json 登録 | ✅ 8/8 |

## 修正が必要な項目

### CRITICAL
なし

### HIGH
なし

### MEDIUM
なし

### LOW
1. **`.claude/settings.json` 不在** — settings.local.json が単独で運用中。機能は完全動作。spec 命名と一致させたい場合は `cp settings.local.json settings.json` で対応可能だが、`.local.json` は git 管理外で局所オーバーライド用途として使う方針なら現状維持で可。
2. **`file-finder` agent が model=haiku** — CLAUDE.md 規約表は sonnet と記載。haiku でも実用上問題ないが、規約と実装のどちらかを揃える必要あり。CLAUDE.md 表を `file-finder` 行のみ haiku に修正するのが軽い対応。
3. **Codex skills (consult/review/rescue) の補足ファイル不足** — SKILL.md 単独。これらは操作系 wrapper であり知識ファイル不要との設計判断は妥当。Spec 要求との差異のみ。
4. **/reimagine, /smart-compact 未実装** — 進捗ファイルの中期 TODO として既知。
5. **`.codex/budget.json.today.date` が 2026-05-07** — 今日 (2026-05-08) はまだ Stop hook が発火していないため未ローテート。次回 Claude セッション終了時に自動ロールオーバー予定。`tokens_used: 13609` は preflight ダッシュボード値と一致。

## 推奨される次のアクション

1. **今すぐの修正不要** — システムは healthy。
2. (任意) CLAUDE.md の agent モデル表で `file-finder` を haiku に変更、または agent ファイルを sonnet に変更して規約と実装を揃える。
3. (任意) 命名揺れが気になる場合 `.claude/settings.json` を導入。
4. **進行中の作業 (`feat/llm-response-cache`) を継続して問題ない**。
