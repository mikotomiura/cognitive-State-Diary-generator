# Findings — tuning-rotation-throughput

**作成日**: 2026-05-08
**入力データ**: `output/`, `output_archive_20260405/`, `output_archive_20260405_pre_run/`, `output_experiment/` の `generation_log.json`
**生成手順**: `python scripts/throughput_report.py output*/generation_log.json`

---

## 1. 計測サマリ（4 ラン）

| Run | Days | Total | P1 | P2 | P2 share | P3 | retries | fallbacks |
|---|---|---|---|---|---|---|---|---|
| `output` (最新) | 7 | **269.8s** | 56.0s | **157.2s** | **58.3%** | 56.6s | 5 | 0 |
| `output_archive_20260405` | 7 | 196.6s | 59.1s | 111.7s | 56.8% | 25.9s | 2 | 0 |
| `output_archive_20260405_pre_run` | 7 | 243.7s | 64.9s | 136.1s | 55.8% | 42.7s | 4 | 0 |
| `output_experiment` | 5 | 180.7s | 41.2s | 105.9s | 58.6% | 33.6s | 3 | 0 |

**1 ラン = 約 3-5 分。チューニング 1 サイクルが体感の長さ。**

---

## 2. 観測 (script の自動所見)

1. **Phase 2 (Content Generation) が時間の 56-59% (平均 57%) を占める → 主ボトルネック**
2. retry 率は Day あたり 0.29-0.71 (平均 0.54)。**0 retry のランは観測されない傾向**
3. **retry の合計スコア lift: 改善 5 / 同点 3 / 悪化 5** (retry 経由でスコアが必ずしも上がっていないケースが 8 件)
4. **Prompt_Generator.md のハッシュが run 間で重複** あり → 同一プロンプトでの再実行が起きている (LLM レスポンスキャッシュの効果余地あり)

---

## 3. プロンプトハッシュ比較（重要発見）

| prompt | output | archive | pre_run | experiment | 状態 |
|---|---|---|---|---|---|
| Prompt_Critic.md         | 0024fa98 | 0024fa98 | 0024fa98 | 0024fa98 | **= 全ラン同一** |
| Prompt_Generator.md      | ffd8f324 | 495cab38 | 495cab38 | ffd8f324 | * 差分あり |
| Prompt_MemoryExtract.md  | 0439e969 | 0439e969 | 0439e969 | 0439e969 | **= 全ラン同一** |
| Prompt_StateUpdate.md    | f8302a9e | f8302a9e | f8302a9e | f8302a9e | **= 全ラン同一** |
| System_MemoryManager.md  | 295f627a | 295f627a | 295f627a | 295f627a | **= 全ラン同一** |
| System_Persona.md        | 57ab81d4 | 57ab81d4 | 57ab81d4 | 57ab81d4 | **= 全ラン同一** |

**含意**:
- **Phase 1 (StateUpdate / Memory) は全 run でプロンプトが同一** にも関わらず、**毎回フル実行されている**
- Phase 2 でも `output` と `output_experiment` は **Generator.md のハッシュが同一** (`ffd8f324`)
- つまり「プロンプト編集 → 再実行」のサイクルでは、**多くの LLM 呼び出しが本来不要**

---

## 4. retry の品質改善効果（限定的）

| run | 改善 | 同点 | 悪化 | 計 |
|---|---|---|---|---|
| 全 4 run 合計 | 5 | 3 | 5 | 13 |

retry 経由でスコアが「上がっていないケース」が **約 62% (8/13)**。
Critic フィードバック連鎖は、**期待されるほど retry 品質を引き上げていない**。
これは前タスク `20260507-best-of-n-parallel/design.md` で「Best-of-N 並列化が連鎖を喪失することの懸念」と
されていたが、本データでは **連鎖の効果自体が限定的** であることが示唆される。

---

## 5. 候補手段の ROI 比較

| # | 手段 | 期待効果 (チューニング回転率) | 実装コスト | 副作用 / リスク | ROI |
|---|---|---|---|---|---|
| 1 | **LLM レスポンスキャッシュ** (input hash → output) | **大**: Prompt_Generator のみ変更時、Phase 1 (P1) と Critic Phase (P3) の **全 6 プロンプトがキャッシュ HIT** で実質 0 秒。1 サイクル 270s → 約 110-150s 程度に短縮見込み (P2 のみ実行) | **中**: LLM クライアント前段にキャッシュ層を追加。disk-based KV (e.g. shelve / sqlite) で十分 | 偽陽性のリスク (input hash 衝突)。temperature が含まれれば確率変動も captured。expire ポリシー要 | **★★★** |
| 2 | **Best-of-N 並列化** (B 案 / C 案) | **中**: retry 率 0.5 前提だと wall-time ≈ 30% 削減見込みだが、API コスト N 倍 | **高**: pipeline.py の中核ロジック改修。前タスクで設計議論を要したレベル | フィードバック連鎖喪失だが、**§4 の通り連鎖効果は限定的なので懸念低下** | **★★** |
| 3 | **固定 seed / temperature=0** | **小-中**: A/B 比較の安定化。生成品質の評価ノイズ削減で **判断回数の削減** に寄与 | **低**: temperature 切替モードを追加するだけ | 多様性消失で品質劣化リスク。本番ではなく評価モード限定 | **★★** |
| 4 | **Day 単位部分実行 / `--day N` 強化** | **中**: 1 Day だけ再走できれば 1 サイクル 25-40s 程度。**ただし `--day N` は既に存在する** (CLAUDE.md) ので、現状活用度の調査が先 | **低-中** (現状把握次第) | Day 1->N の state 引き継ぎが要 cache | **★★★** (現状活用次第) |
| 5 | **dry-run の強化** | **小**: 構造のみ検証で品質判断はできない | **低** | チューニング判断には情報不足 | ★ |
| 6 | **Phase 1 / Phase 3 の per-attempt 計測** (instrumentation) | **小**: さらなる調査用。直接的に時間は短くならない | 低 | 過剰計測のオーバーヘッド微小 | ★ |

---

## 6. 採用案（推奨順）

### 1st: LLM レスポンスキャッシュ

- **§3 の発見が決定打**: 6 プロンプトのうち 4 は全 run で同一、Generator も run 間で重複あり。
  キャッシュ HIT 率が極めて高い。
- 実装は LLM クライアント前段の薄い decorator で済み、pipeline.py 改修不要。
- 後続タスク名候補: **`feat/llm-response-cache`**
- スコープ: `csdg/engine/llm_client.py` への disk-based KV キャッシュ層追加。
  - キー: `(prompt_hash, model, temperature, max_tokens, ...)` の正規化ハッシュ
  - ストア: `~/.cache/csdg/` 配下の sqlite or shelve
  - `--no-cache` フラグで bypass 可能
  - チューニング時は temperature を含めるか議論（含めると HIT 率↓、含めないと確率変動を失う）

### 2nd: `--day N` の現状調査 + 部分実行強化

- 既に存在するため、まず **現状活用度の調査** が必要 (本タスク内で出来ていない)
- もし state 引き継ぎが未実装なら、Day i の最終状態を保存・再利用する仕組みが必要
- 後続タスク名候補: **`feat/day-resume-from-cache`**
- スコープ: `output/` 配下に `state_snapshots/day_N.json` を残し、`--day N` 起動時に prev_state を復元

### 3rd: 固定 seed / temperature=0 モード

- 評価サイクルの判定ノイズ削減用
- 後続タスク名候補: **`feat/deterministic-eval-mode`**

### Best-of-N 並列化は当面ペンディング

- ROI は ★★ 止まり。キャッシュで P1+P3 を消すほうが回転率向上に効く
- §4 の retry 連鎖の効果限定が確認できれば、将来再開する価値は残る

---

## 7. 後続タスクへの引き継ぎ

| 推奨ブランチ | スコープ | 優先度 |
|---|---|---|
| `feat/llm-response-cache` | LLM クライアント前段の disk-based KV キャッシュ層 | **High** |
| `feat/day-resume-from-cache` | `--day N` での state 復元、Day 単位再走の高速化 | Mid |
| `feat/deterministic-eval-mode` | 固定 seed / temp=0 の評価モード | Mid |
| `feat/best-of-n-parallel` (再開) | 前タスクの Option B/C を再検討 (キャッシュ導入後の評価次第) | Low |

各タスク開始時は、本 findings.md と前タスク `20260507-best-of-n-parallel/design.md` を参考資料として参照すること。

---

## 8. 検証コマンド

```bash
# 単一ラン
python scripts/throughput_report.py output/generation_log.json

# 4 ラン横並び比較 (本ファイル生成元)
python scripts/throughput_report.py \
    output/generation_log.json \
    output_archive_20260405/generation_log.json \
    output_archive_20260405_pre_run/generation_log.json \
    output_experiment/generation_log.json
```

---

## 9. 制約 / 限界

- **サンプル数 4 ラン** と少ない。判断は予備的。本格調査前にラン数を倍増する余地あり
- LLM レイテンシの run 間揺らぎは大きい。**絶対値より shares (%) を重視**
- per-attempt の P1/P2/P3 内訳は未取得 (Day 単位集計のみ)
- API コスト (実額) の集計は未対応 (token / dollar)
