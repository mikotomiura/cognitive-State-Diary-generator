# Design — fix-codex-wrapper

(`/implement fix` の Step 1「再現と原因特定」で確定する。下は仮説。)

## 仮アプローチ

Wrapper の `-m gpt-5` ハードコードを **環境変数 `CODEX_MODEL` 経由** で動的に切替可能にする。空文字列の場合は `-m` 引数自体を省略し、Codex CLI の認証状態に応じた自動選択に委ねる。

## 検討した代替案

| 案 | 採否 | 理由 |
|---|---|---|
| **A: env 経由 + デフォルト=gpt-5** | (推奨) | 後方互換 (既存 API key ユーザーの動作不変)、運用切替容易、AGENTS.md の gpt-5 想定を維持 |
| B: `-m` を完全削除 (常に CLI 自動) | 不採用 | API key 環境で意図通り動く保証が消える、提言の質低下リスク |
| C: 認証状態を検出して自動切替 (`codex login status` をパース) | 不採用 | wrapper の複雑化、CLI バージョン依存、テスト困難 |
| D: `.codex/config.toml` に `model =` を残し wrapper の `-m` だけ削除 | 不採用 | config の値が wrapper まで伝搬する保証は CLI 仕様依存。env 経由のほうが明示的 |

## 仮実装

```bash
# scripts/run-codex-{consult,review}.sh の `exec codex exec` 直前に追加
# CODEX_MODEL 未設定時は config.toml 既定 (gpt-5) を維持
CODEX_MODEL="${CODEX_MODEL-gpt-5}"
MODEL_ARGS=()
if [ -n "$CODEX_MODEL" ]; then
  MODEL_ARGS=(-m "$CODEX_MODEL")
fi

exec codex exec \
  --sandbox read-only \
  "${MODEL_ARGS[@]}" \
  -c model_reasoning_effort=... \
  "$INPUT"
```

ポイント:
- `${VAR-default}` (`-` であって `:-` ではない) で **未設定** と **空文字列** を区別
- 配列展開 `"${MODEL_ARGS[@]}"` で空配列なら何も渡らない (`-m` 引数自体スキップ)

## 変更ファイル一覧

| ファイル | 変更内容 | 影響範囲 |
|---|---|---|
| `scripts/run-codex-consult.sh` | `-m gpt-5` を env 経由に | `codex-consult` Skill |
| `scripts/run-codex-review.sh` | 同上 | `/cross-review` / `cross-reviewer` agent |
| `.codex/config.toml` | `model = "gpt-5"` 直前に運用メモコメント追記 | ドキュメント |
| `AGENTS.md` (Codex CLI 固有指示) | モデル表 (L13-15) に `CODEX_MODEL` env 1 行追記 | Codex 操作者向け |

## データフロー

```
User → /cross-review
     → cross-reviewer agent
       → run-codex-review.sh
         ↓ 環境変数を読む
         CODEX_MODEL="" → -m 省略 → CLI 自動選択 (ChatGPT auth: o1 系? gpt-5o-mini?)
         CODEX_MODEL=gpt-5 → -m gpt-5 → API key auth で gpt-5
         CODEX_MODEL=o1 → -m o1 → 任意モデル
         ↓
       → codex exec
```

## リスク / トレードオフ

- **後方互換性**: env 未設定なら `gpt-5` がデフォルト → 既存 API key ユーザーは挙動不変
- **テスト**: 実 codex 起動を伴うテストは CI で再現困難。wrapper のロジックは shell スクリプトのため pytest 範囲外。手動疎通 (`/cross-review` 実行) で確認
- **shellcheck**: `${VAR-default}` の慣習や配列展開を shellcheck が誤検出しないか検証
- **ドキュメント整合**: AGENTS.md / `.codex/config.toml` / steering decisions.md の 3 箇所で env 仕様を一貫させる

## 未確定事項 (Step 0/1 で確定)

- 現行 wrapper が他に env 経由のオプション/フラグを持つか
- `codex-rescue` Skill (manual) の手順書に env 切替を案内するか
- `/verify-setup` の Codex 疎通検証スクリプトに env 切替テストを追加するか (本タスクのスコープ拡張)
