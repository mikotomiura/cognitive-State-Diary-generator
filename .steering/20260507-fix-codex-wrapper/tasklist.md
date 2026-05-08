# Tasklist — fix-codex-wrapper

## Step 0/1: 再現と原因特定

- [x] 症状確認: `echo "1+1" | codex exec -m gpt-5` で 400 error
- [x] 成功条件確認: `codex exec -m gpt-5.5` → 動作 (gpt-5.5 が ChatGPT 認証下でも利用可)
- [x] 認証状態確認: `codex login status` → `Logged in using ChatGPT`
- [x] PR #14 で wrapper が `-m gpt-5` を強制した経緯を特定 (`bbc75b3`)

## 実装 (1 文字置換 × 9 箇所)

- [x] `scripts/run-codex-consult.sh` — `-m gpt-5` → `-m gpt-5.5`
- [x] `scripts/run-codex-review.sh` — `-m gpt-5` → `-m gpt-5.5`
- [x] `.codex/config.toml` — `model = "gpt-5"` → `model = "gpt-5.5"` + 経緯コメント
- [x] `AGENTS.md` モデル表 (consult/review/rescue) — `gpt-5` → `gpt-5.5`
- [x] `AGENTS.md` 入力データ制約節 — 「外部 LLM (gpt-5)」 → `(gpt-5.5)`
- [x] `AGENTS.md` rescue 例 — `-m gpt-5` → `-m gpt-5.5`
- [x] `.claude/agents/cross-reviewer.md` — gpt-5 言及 2 箇所
- [x] `.claude/skills/codex-review/SKILL.md` — description gpt-5
- [x] `.claude/skills/codex-consult/SKILL.md` — description + 入力制約節
- [x] `.claude/skills/codex-rescue/SKILL.md` — description + 例

## 検証 (実起動)

- [x] `bash -n scripts/run-codex-{consult,review}.sh` syntax OK
- [x] `echo "1+1" | scripts/run-codex-consult.sh` → `2` を返す (gpt-5.5、12,080 tokens、env 不要)
- [x] cross-review 経路 (env 機構撤去前の段階) で Codex 実起動成功確認済 (CRITICAL 0 / HIGH 1 / MEDIUM 2 / LOW 1)
- [x] `pytest tests/` 緑 (531 passed、本タスクは shell + ドキュメントのみで Python 無影響)
- [ ] shellcheck — 環境未インストールのため skip

## ドキュメント

- [x] AGENTS.md モデル表 + 注記 (動作確認モデルと根拠)
- [x] `.codex/config.toml` 経緯コメント
- [x] `decisions.md` 作成 (D1: 単純置換採用 / D2: env 機構撤去経緯 / D3: cross-review 結果 / D4: テスト戦略 / D5: budget.json 除外)

## 仕上げ

- [x] requirement.md / design.md は実装方針変更後の更新不要 (本質要件は不変、実装は 1 文字置換に簡略化)
- [x] コミットメッセージ準備 (`fix(codex): wrapper のモデル指定を gpt-5.5 に変更`)
- [x] `/finish-task` でコミット実行 (c7d15fb)
