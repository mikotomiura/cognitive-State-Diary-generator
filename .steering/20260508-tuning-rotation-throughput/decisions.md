# Decisions — tuning-rotation-throughput

このタスクで意図的に下した設計判断を記録する。

---

## D-01: テストから private 関数 (`_get_records` / `_phase_totals` 等) を直接 import する

**日付**: 2026-05-08
**コンテキスト**: code-reviewer から「`_` プレフィックス関数の直接テストはプロジェクト慣習に反する。
公開 API (`generate_report`) 経由での振る舞い検証を推奨」との指摘 (H-02 相当)。

**判断**: **現状維持** — private 関数の直接 import を許容する。

**理由**:
1. `scripts/throughput_report.py` の公開 API は事実上 `generate_report` のみで、
   集計ヘルパは pure 関数群。
2. `generate_report` の出力は人間可読の文字列で、振る舞い検証には部分文字列マッチが必要になり、
   集計ロジックの誤りを精緻に捕捉しにくい。
3. 集計関数は単純な型と入出力で、AAA テストとの相性が良い。
4. `scripts/quality_report.py` 側にテストが存在しないため、参照可能な慣習が無い。

**代替案として検討した内容**:
- 関数を `_` なしの公開関数 (`get_records` / `phase_totals` 等) に昇格させる
  → 公開 API 表面を不必要に広げるため不採用
- `__all__` で明示的に公開化
  → 同上

**今後の更新条件**: 別の `scripts/*.py` にテストが追加され、
公開 API 経由テストの慣習が確立されたら、本判断を再評価する。

---

## D-02: LLM レスポンスキャッシュを採用案 1st とする (Best-of-N 並列化より優先)

**日付**: 2026-05-08
**コンテキスト**: 前タスク `20260507-best-of-n-parallel` では Best-of-N 並列化を主候補としていたが、
本タスクの計測で「6 プロンプト中 5 つが全 run で同一ハッシュ」「Generator.md も run 間で
重複するケースあり」という強いキャッシュ HIT 期待値が判明した。

**判断**: 後続実装タスクの優先順位を以下とする:
1. **`feat/llm-response-cache`** — LLM クライアント前段に disk-based KV キャッシュ層
2. `feat/day-resume-from-cache` — `--day N` 強化 + state 復元
3. `feat/deterministic-eval-mode` — 固定 seed / temp=0 の評価モード
4. `feat/best-of-n-parallel` (再開) — キャッシュ導入後の評価次第

**理由**:
- キャッシュは pipeline.py 改修不要（LLM クライアント前段の薄い decorator で済む）。
  実装コスト低 × 期待効果大 で ROI 最高。
- Best-of-N 並列化は API コストが N 倍になり、フィードバック連鎖の喪失リスクもある。
  本タスクの retry lift 計測 (改善 5 / 同点 3 / 悪化 5) で
  「連鎖効果は限定的」と示唆されたが、それでもキャッシュより ROI は劣る。
- キャッシュ導入後に「P2 が依然ボトルネックである」ことが再確認できれば、
  そのとき初めて並列化を再検討するのが合理的。

**詳細**: `findings.md` の §5 ROI 比較表 / §6 採用案 / §7 後続タスク。
