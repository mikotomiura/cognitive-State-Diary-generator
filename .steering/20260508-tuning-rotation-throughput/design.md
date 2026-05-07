# Design — tuning-rotation-throughput

## アプローチ

**3 フェーズで進める。本タスクのスコープは Phase A + B のみ。Phase C は後続タスク。**

### Phase A: 既存ログの分析（コード追加なし、まず予備所見を得る）

既存資産:

- `output/generation_log.json` (7 Day, 5 retries, 270s)
- `output_archive_20260405/generation_log.json` (7 Day, 2 retries, 197s)
- `output_archive_20260405_pre_run/generation_log.json` (7 Day, 4 retries, 245s)
- `output_experiment/generation_log.json` (5 Day, 3 retries, 181s)

これらだけで Phase 1/2/3 内訳・retry 分布・retry スコア改善・プロンプトハッシュ変化はカバーできる。
コード追加なしで予備所見が得られるため、最初に手を付ける。

### Phase B: 計測スクリプト追加 + 報告書作成

- `scripts/throughput_report.py` を新設（`quality_report.py` と同形式）
  - 入力: `generation_log.json` の 1 つ以上（複数指定で run 比較）
  - 出力 (stdout):
    - Phase 1/2/3 の総時間と shares (%)
    - Day 別タイミング表（retry 含む）
    - retry 分布（0/1/2/3+ retries の Day 数）
    - retry スコア lift（attempt 0 vs 最終 attempt の合計スコア差分）
    - プロンプトハッシュ比較表（複数ラン指定時のみ。同一/相違を可視化）
    - 観測サマリ（ボトルネック仮説）
  - exit code: `quality_report.py` 同様 (0 = 正常出力, 2 = 引数エラー)
- `.steering/20260508-tuning-rotation-throughput/findings.md` を成果物として残す
  - Phase A + B の出力と、候補手段の ROI 比較表、採用案（または採用順）を記述

### Phase C: 採用案の実装（**後続タスク** — 本タスク対象外）

findings.md の採用決定を受けて別タスクで実装:

- 例 1: `feat/llm-response-cache` — LLM レスポンスキャッシュ層
- 例 2: `feat/best-of-n-parallel` — 既タスクの再開（Option B/C 案）
- 例 3: `feat/fixed-seed-mode` — temperature=0 / 固定 seed の comparison mode

---

## 予備所見（Phase A の手早い結果）

| Run | Days | Retries | P1 total | P2 total | P3 total | Total |
|---|---|---|---|---|---|---|
| output (最新) | 7 | 5 | 56s | **157s (58%)** | 57s | 270s |
| archive_20260405 | 7 | 2 | 59s | **112s (57%)** | 26s | 197s |
| archive_pre_run | 7 | 4 | 65s | **136s (66%)** | 43s | 245s |
| experiment | 5 | 3 | 41s | **106s (61%)** | 34s | 181s |

**観測**:
- **Phase 2（生成）が常に時間の 57–66%** を占める → P2 が主ボトルネック
- 1 ラン = 約 3–5 分、retry ありの Day で P2/P3 が伸びる
- prompt_hash は run 間で変わっており、プロンプト編集 → 再実行のサイクルが回っているのが確認できる
- retry 0 件のランは存在しない（どのランでも 2–5 回 retry が発生）

これらは findings.md に詳細表で残す。

---

## 検討した代替案（本タスクのアプローチ選択）

| 案 | 採否 | 理由 |
|---|---|---|
| 既存ログ分析 + 報告書（Phase A+B） | **採用** | 既存資産だけで動機（チューニング回転率）の起点となる現状把握が完結する。最小コストで最大の判断材料を得られる |
| `pipeline.py` に新規 metrics を追加してから計測 | 不採用 | Phase 1/2/3 timing と attempts は既に永続化されており追加不要。RetryCandidate 単位の per-attempt 詳細が欲しくなったら別途検討 |
| マイクロベンチマーク追加 | 不採用 | 本番ログがあるのにマイクロベンチを書くのは過剰。LLM レイテンシは外部 API 依存で再現性が低い |
| 採用案の実装まで一気通貫 | 不採用 | 動機が「ROI 比較で採用案を決める」なので、実装を急ぐと比較の意味が消える |

---

## 変更ファイル一覧

| ファイル | 変更内容 | 影響範囲 |
|---|---|---|
| `scripts/throughput_report.py` | 新規追加。CLI で `generation_log.json` を 1+ 受け取り、報告書を stdout 出力 | 既存パイプライン無影響。`quality_report.py` と並列で運用 |
| `tests/test_throughput_report.py` | 新規追加。fixture log を使った AAA テスト（集計・retry 分布・hash 比較） | 新規 |
| `.steering/20260508-tuning-rotation-throughput/findings.md` | 新規追加。報告書（Phase A+B の最終出力） | .steering 配下のみ |
| `csdg/` 配下 | **変更なし** | — |
| `prompts/` 配下 | **変更なし** | — |
| `schemas.py` | **変更なし**（破壊的変更禁止） | — |

---

## データフロー / インターフェース変更

なし。本タスクは既存 `PipelineLog` (`csdg/schemas.py`) を読み取る分析専用スクリプトの追加のみ。
スキーマ変更なし、API 変更なし、ランタイム挙動変更なし。

---

## テスト戦略

- `tests/test_throughput_report.py`:
  - `_load_log` で正常な generation_log.json を読み込めること
  - Phase 1/2/3 の合計と share 計算が正しいこと
  - retry 分布が正しく集計されること
  - 同一/異なる prompt_hash の比較が正しく動作すること
  - 引数なし/存在しないファイルで exit code 2
- 既存テストへの影響なし（新規ファイルのみ追加）

---

## リスク / トレードオフ

| リスク | 対応 |
|---|---|
| 4 ランは少サンプル。判断材料として十分か | findings.md の結論を「予備的」と明記。必要なら追加ランを別途取得（但し本タスクでは行わない） |
| Phase 1/2/3 の per-attempt 内訳が無く、「retry 中の P2 / P3 比率」が見えない | 必要性が判明したら別タスクで instrumentation 追加。現時点では Day 単位の集計で十分と判断 |
| LLM レイテンシの揺らぎで run 間比較がノイジー | 「絶対値より shares (%) を見る」と findings.md に注記 |
| 採用案が決まっても本タスクでは実装しない（中途半端感） | 後続タスクのスコープ・ブランチ命名を findings.md 末尾に明記 |

---

## 完了の判断基準

- `scripts/throughput_report.py` が 4 ランすべてで正しく動作する
- `tests/test_throughput_report.py` が緑
- `mypy csdg/ --strict` / `ruff check csdg/` / `ruff format --check csdg/` 通過
- `findings.md` に候補手段の ROI 比較表と採用案（または採用順）が記述されている
- 後続タスクの推奨ブランチ命名が findings.md 末尾に書かれている
