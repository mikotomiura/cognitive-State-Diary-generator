# Claude Code 環境構築 進捗

このファイルは新 verify-setup 仕様 (Phase 0-9) に基づく状態を記録する。
旧 7 段階で構築されたリポジトリを 2026-05-07 に再評価し、Phase 5 (Codex Bridge) を追加構築した経緯を含む。

## フェーズ完了状況

- [x] **Phase 0: bootstrap** — 進捗ファイル生成
  - 完了日時: 2026-05-07 (旧構築は遡及記録)
  - 注: 旧 Phase 0-7 (8 段階) で 2026-03-24 〜 2026-04-09 に初回構築済。本ファイルは新仕様 (10 段階) 移行時に追加。
- [x] **Phase 1: docs** — 5 必須 + 2 補助 (4,857 行) 構築済
  - 完了日時: 2026-03-25 (旧構築)
- [~] **Phase 2: marketplace** — `docs/external-skills.md` 空テンプレ生成 + 公式 plugin **未導入**
  - 完了日時: 2026-05-07 (再評価時)
  - 状態: 現時点で PDF/Office/Web testing 等の公式 Skill は不要と判断。将来必要になった時点で `/setup-marketplace` で再評価する。
- [x] **Phase 3: CLAUDE.md / AGENTS.md / agent-shared.md** — 3 ファイル体制
  - 完了日時: 2026-05-07 (CLAUDE.md は旧構築済 / AGENTS.md と agent-shared.md は新規追加)
- [x] **Phase 4: skills** — 4 自前 Skill (python-standards, pydantic-patterns, prompt-engineering, test-standards) + ネスト平坦化
  - 完了日時: 2026-03-25 (構築) + 2026-05-07 (平坦化)
  - 注: 動的 Skill 追加は中期 TODO
- [x] **Phase 5: codex-bridge** — Codex CLI 連携基盤構築
  - 完了日時: 2026-05-07
  - 構成: `.codex/config.toml` / `.codex/budget.json` / `scripts/secrets-filter.sh` / `scripts/run-codex-{consult,review}.sh` / 3 codex skills / cross-reviewer agent / `/cross-review` command / 3 codex hooks
  - ローカル環境: codex-cli 0.125.0 (`/opt/homebrew/bin/codex`)
- [x] **Phase 6: agents** — 9/9 基本エージェント + cross-reviewer (Phase 5 連動)
  - 完了日時: 2026-03-25 (旧構築) + 2026-05-07 (cross-reviewer 追加 + レビュー系 opus 昇格)
- [x] **Phase 7: commands** — 主要コマンド + /cross-review (Phase 5 連動)
  - 完了日時: 2026-03-25 (旧構築) + 2026-05-07 (/cross-review 追加)
  - 注: `/add-feature`, `/fix-bug`, `/refactor` は `/implement` に統合済 (c142b74)。`/smart-compact` `/reimagine` は LOW 項目として未着手。
- [x] **Phase 8: hooks** — 3 層構成 + Codex 第 4 層
  - 完了日時: 2026-04-09 (旧 2 hook) + 2026-05-07 (3 層 + Codex hook 追加 + Stop を type:command 化)
- [x] **Phase 9: verify-setup** — 整合性検証
  - 完了日時: 2026-05-07
  - 検証結果: 本ファイル更新後に再実行予定

## ライセンス同意ログ

(該当なし — proprietary plugin 未導入)
