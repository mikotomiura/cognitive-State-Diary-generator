# Decisions — feat-llm-response-cache

## D-01: /reimagine パターンで Codex に独立設計案を依頼

**日時**: 2026-05-08
**判断**: Claude が初回設計 (v1) を書いた後、anchor バイアスを排除するため `codex-consult` で
gpt-5.5 に **`requirement.md` の抜粋のみ** を渡し独立設計案 (v2) を取得。両案を比較してマージ案 (v3) を採用した。

**Why**: 1 名（1 LLM）の設計判断にはバイアスが乗りがち。重要な技術選定（ストレージ・キー設計・
シリアライズ形式）で「最初に思いついた案」が無批判に採用されるリスクを排除するため。
ユーザーから「破壊と構築 (= /reimagine)」と「Codex review」の併用を明示要求された。

**How to apply**: V1 設計確定後、別 LLM (Codex) に同じ requirement だけを渡して独立設計を取得。
v1/v2 比較表を作成し、ユーザー承認のもとマージ案を確定。アーカイブとして `design-v1-claude.md` /
`design-v2-codex.md` を残す。

---

## D-02: v3 マージで採用した v2 (Codex) からの 4 改良点

**日時**: 2026-05-08

| 改良点 | v1 (Claude) | v3 採用 | 理由 |
|---|---|---|---|
| `temperature` の正規化 | float のまま | **`repr(float)` で文字列化** | 0.7 と 0.7000000001 等の表現揺れによる誤 MISS 防止 |
| `cache_format_version` | なし | **`"1"` を追加** | 将来のスキーマ変更で旧キャッシュ全自動失効 (DB drop 不要) |
| 保存形式 | BLOB | **TEXT JSON `{kind, payload}`** | sqlite `.dump` で inspect 可能、デバッグ性 |
| stampede 対策 | 言及なし | **コメントに先送り記載** | V1 は逐次パイプラインで競合発生せず、Best-of-N 復活時の TODO に記録 |

**Why**: Codex が指摘した 4 点はいずれも v1 の盲点で、コストが小さく将来リスクを下げる効果が大きい。
特に `cache_format_version` は schema 変更時の運用コストを劇的に下げる (`rm -rf ~/.cache/csdg/llm/` 不要)。

**How to apply**: 後続のキャッシュ層実装で全 4 点を反映。stampede 対策のみ V1 では不要だが、
Best-of-N 並列化が将来戻ってきた時の必須対応として `cache.py` のコメントに残す。

---

## D-03: schemas.py の `cached: bool` フラグ追加は V2 に先送り

**日時**: 2026-05-08

`GenerationRecord` への `cached: bool` フィールド追加は V1 では実施しない。

**Why**: schemas.py は CLAUDE.md 禁止事項「破壊的変更を無断で行わない」の対象。新規フィールド
追加は default value 付きでも既存 551 件のテスト・JSON ファイル後方互換を慎重に検証する必要があり、
キャッシュ機能のコアパスから切り離せる。`logger.info("[cache HIT/MISS]")` 出力 + Phase duration の
自然短縮で `throughput_report.py` が効果を計測できる。

**How to apply**: V1 では log 文字列のみで識別。V2 で必要になれば schema 変更を別タスクとして切り出す。
