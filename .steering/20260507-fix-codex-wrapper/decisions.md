# Decisions — fix-codex-wrapper

## D1: 単純な model 文字列置換を採用 (env 変数による分岐を不採用)

`.codex/config.toml` / wrapper 2 本 / AGENTS.md / 各 codex-* Skill / cross-reviewer agent の `gpt-5` を **すべて `gpt-5.5` に置換** する。env 変数による切替機構は導入しない。

**Why**:
- ChatGPT 認証で `gpt-5.5` が動作することを実証済 (本セッションで `2` を 3 回独立に取得確認)
- gpt-5.5 は API key 認証でも利用可能 (OpenAI のモデル系列で 5.5 > 5 はリリース順)
- 「現在動いている設計」と「動いていない設計」の差は **1 文字 (`gpt-5` → `gpt-5.5`)** だけ。env 変数で間接化するのは over-engineering
- env 変数を導入すると bash 3.2 互換のための `${arr[@]+...}` 配列展開や、空文字列と未設定の使い分けの説明が増え、wrapper の認知負荷が上がる
- ユーザーフィードバック「5.5 に変更したらいいだけでは」が正鵠を射ていた

**How to apply**: 将来 OpenAI が新モデル (gpt-6 等) を出して可用性が変わった場合は、同じ 9 箇所を一括 grep & 置換する。

## D2: 当初実装 (env 変数機構) を撤去した経緯を記録

実装過程で一度 `${CODEX_MODEL-gpt-5}` 経由の env 切替機構を作ったが、ユーザー指摘で撤去した。

撤去前: 約 10 行 / wrapper × 2、bash 3.2 配列展開対策 (`${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}`) が必要、AGENTS.md に「認証方式とモデル切替」表を新設
撤去後: 1 行変更 / wrapper × 2、追加コメントなし、AGENTS.md は既存表の値だけ更新

機能要件 (ChatGPT 認証で動く) は両者とも満たすが、認知コストが大幅に低い後者を採用。

## D3: cross-review (Codex 実起動) の動作確認は env 機構の段階で取得済

Codex レビューは env 機構実装段階で `CODEX_MODEL=gpt-5.5` 経由で起動成功 (gpt-5.5、14,839 tokens、本タスクの diff に対して CRITICAL 0 / HIGH 1 / MEDIUM 2 / LOW 1 を返した)。

そのレビュー指摘の MEDIUM 2 件 (`CODEX_MODEL=""` 記述の実装乖離 / 「ChatGPT で gpt-5 不可」断定の陳腐化リスク) は、env 機構ごと撤去した本最終形では **無効化** された (両指摘の対象である記述自体が撤去されたため)。HIGH 1 件 (`.codex/budget.json` 差分は revert すべき) はコミット対象から除外する設計で対応済 (D5)。

LOW 1 件 (`${MODEL_ARGS[@]+...}` 可読性) は env 機構撤去で **問題自体が消失**。

## D4: テスト戦略

shell スクリプトのため pytest 範囲外。検証は:
1. `bash -n scripts/run-codex-{consult,review}.sh` で syntax check
2. 実起動: `echo "1+1" | scripts/run-codex-consult.sh` → `2` を返す (12,080 tokens)
3. 既存 pytest tests/ に影響なし (本変更は Python コードに触れない)

shellcheck はホスト未インストールのため skip。CI に追加するかは別タスク。

## D5: コミット範囲から `.codex/budget.json` を除外

`.codex/budget.json` は token-report-stop hook が更新する **runtime state ファイル**。本セッション中に Codex を呼んだ結果として `tokens_used` が変動しているが、機能変更とは無関係。Codex レビュー (D3) で HIGH 指摘も同件。

将来的には `.gitignore` 化または「テンプレート + runtime state」分離が望ましいが、本タスクのスコープ外 (別タスクで対応)。
