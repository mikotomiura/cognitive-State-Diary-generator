# Design — best-of-n-parallel

**ステータス: クローズ — 2026-05-08（最終結論は本ファイル末尾を参照）**

タスク名「best-of-n-parallel」が示唆する単純な並列化が、現行コードでは振る舞い変更を伴うことが
判明した。実装に入る前に方針を再議論し、結果として **動機が「並列化そのもの」ではなく
「チューニング回転率」だった** ため、本タスクはクローズし、より広いスコープの後続タスクへ
バトンタッチする方針となった。

本ドキュメントは現状コードの分析と並列化アプローチの整理を **そのまま後続タスクの参考資料** として
残しておく。

---

## 現状コードの分析

対象: `csdg/engine/pipeline.py` の `PipelineRunner.run_single_day()` (L914-1276)。

### 実態は「逐次リトライ + フィードバック連鎖 + フォールバック Best-of-N」

```
while attempt_idx < self._config.max_retries:
    temperature = schedule[attempt_idx]                      # 段階的下降
    if is_high_impact and ...persona_deviation < 3:         # 前 attempt の結果に依存
        temperature = max(temperature, initial_temperature)

    diary = await actor.generate_diary(
        revision_instruction=revision_instruction or feedback,  # 前 attempt の Critic 指摘
        ...
    )
    critic_score = await critic.evaluate_full(diary, ...)

    if judge(critic_score):
        # 構造違反があればボーナス再試行 (1回のみ)
        if structural_violations and not structural_retry_used:
            revision_instruction = _sanitize_revision(violation_text + hook_guidance)
            continue                                        # attempt_idx 据え置き
        ...
        if len(candidates) > 1:
            best = self._select_best_candidate(candidates)  # ボーナス再試行後の選択
        break                                                # 早期終了

    revision_instruction = critic_score.revision_instruction  # フィードバック更新
    attempt_idx += 1
else:
    best = self._select_best_candidate(candidates)          # 全リトライ消費後のフォールバック
    fallback_used = True
```

### 「Best-of-N」と呼ばれる箇所は 2 つだけ

1. **構造違反ボーナス再試行後** (L1182-1197): 通常は 1 候補だが、ボーナスで 2 候補になった時のみ
2. **全リトライ消費後のフォールバック** (L1227-1236): Critic が一度も Pass しなかった時の救済

つまり **N 候補を毎回作って最高を選ぶ Best-of-N** ではない。typical pass では 1 候補で終了し、
Best-of-N 的な選択は failure 時の fallback でしか発生しない。

### 候補間の依存関係

各 attempt は **前 attempt の結果に依存** している:

| 依存ポイント | 詳細 | 並列化への影響 |
|---|---|---|
| `revision_instruction` | 前 attempt の Critic `revision_instruction` または `reject_reason` を次の Generator にフィードバック (L1212-1224) | 失う = 同じ失敗を繰り返す確率増 |
| `pending_structural_violations` | 構造違反指摘を次の生成へ持ち越し (L1043, L1077) | 失う |
| `feedback` | 過去の低スコアパターンを critic_log から抽出 (L1037-1039) | これは事前固定なので並列化に影響なし |
| Temperature schedule | `schedule[attempt_idx]` で attempt_idx 増加時に温度下降 (L1047) | 並列化なら全候補に違う温度を割当 (1 対多) |
| 高インパクト分岐 | `len(candidates) == 1 and persona_deviation < 3` で温度維持 (L1050) | 失う |
| 早期終了 | Critic Pass で `break` (L1200) | 失う = 常に N 回 LLM 呼ぶ → API コスト N 倍 |

---

## 並列化アプローチの選択肢

### Option B: 真・並列 Best-of-N（純粋な振る舞い変更）

```python
# 概念
candidates = await asyncio.gather(*[
    generate_and_evaluate(temperature=schedule[i]) for i in range(N)
])
best = max(candidates, key=score)
```

| 指標 | 効果 |
|---|---|
| ウォールクロック | N 倍速 (理想時) |
| API 呼び出し回数 | 常に Phase 2 + Phase 3 を N 回 = 既存比 おそらく N/平均attempts 倍に増 |
| Critic フィードバック連鎖 | 失う |
| 早期終了 | 失う |
| 出力品質 | 不明（要 KPI 計測） |

**懸念**: Critic フィードバック連鎖が「同じ失敗パターンを学習する」設計の根幹だった場合、
1 候補×3 attempts よりも 3 候補×1 attempt の方が劣るシナリオが想定される (各候補が独立に
同じ失敗をする = 多様性低下)。

### Option C: ハイブリッド（初回 N 並列 → 失敗時逐次フォールバック）

```python
# 概念
# 第1ラウンド: N 並列
candidates_round1 = await asyncio.gather(*[generate_and_evaluate(...) for _ in range(N)])
passing = [c for c in candidates_round1 if judge(c.score)]
if passing:
    return select_best(passing)

# 第2ラウンド以降: 既存の逐次リトライ (revision_instruction を最低スコア候補から構築)
revision = build_revision(min(candidates_round1, key=score).score)
... (既存ループ)
```

| 指標 | 効果 |
|---|---|
| ウォールクロック | 初回 Pass 時 N 倍速、失敗時は既存と同等 |
| API コスト | 増（初回常に N 回）。ただし初回 Pass 率が高ければ retry 削減で相殺 |
| Critic フィードバック連鎖 | 部分保持（第2ラウンド以降） |
| 早期終了 | 第1ラウンド内では失う、ラウンド間では維持 |
| 実装複雑度 | 高 |

### Option D: I/O 並列化のみ（振る舞い不変）

| 候補 | 効果 |
|---|---|
| `_compute_prompt_hashes` の I/O 並列 | 起動時 1 回のみ → 効果軽微 |
| Phase 1 と Phase 2 のオーバーラップ | Phase 2 は Phase 1 の出力を使うので不可 |
| 構造違反検出の並列化 | CPU バウンド・既に高速 → 効果なし |

→ **D 案は実質ノーゲイン**。

---

## オープン論点（次回議論用）

1. **真の動機は何か?** ウォールクロック短縮それ自体か、それともプロンプトチューニングサイクルの
   回転率向上か。後者なら、並列化以外の手段（Critic 呼び出しのキャッシュ、Day を跨いだ並列化、
   --dry-run の活用、固定 seed の導入）も比較対象に入る。

2. **API コスト予算は?** Option B/C は API コール増を伴う。`/finish-task` 時の予算チェックを
   越えないか確認が必要。`.codex/budget.json` は Codex 用なので、Anthropic/Gemini 側の予算は
   別管理。

3. **Critic フィードバック連鎖の効果は実測されているか?** ログを見て「retry で品質が改善する
   ケース」がどれだけあるかを定量化すべき。改善が稀なら Option B のロスは小さい。

4. **N の値は?** `max_retries` (現在いくつ?) と同値にすべきか、別途定義すべきか。

5. **Day 間の並列化は検討対象か?** Day 1 → Day 7 は state を引き継ぐため逐次必須。ただし
   `--dry-run` や複数イベントセットの A/B 評価では Day 間並列が可能 → 別タスク化する価値あり。

---

## 採否決定（最終）

| 案 | 採否 | 理由 |
|---|---|---|
| A) 議論保留 | 不採用 | 動機判明により判断可能になった |
| B) 真・並列 Best-of-N | **不採用（本タスク内）** | 動機がチューニング回転率と判明し、Best-of-N 並列化は手段の一候補に過ぎないことが明確になった。他の手段との比較が前提となるため、本タスクのスコープでは判断保留 |
| C) ハイブリッド | **不採用（本タスク内）** | 同上 |
| D) I/O 並列のみ | 不採用 | 実質ノーゲイン |

## 変更ファイル一覧

（コード変更なし — 本タスクはクローズ）

---

## 最終結論（2026-05-08）

### 動機の確認結果

並列化の真の動機は **「プロンプトチューニング回転率の向上」** であり、
本番ウォールクロック短縮や API コスト削減ではない。

### スコープ判断

「Best-of-N 並列化」は手段の一候補に過ぎず、以下のような他の手段が同列の比較対象になる:

- LLM レスポンスキャッシュ (input hash → output) — 同一プロンプトでの再実行を高速化
- 固定 seed / temperature=0 — 比較評価の安定化と分散の縮小
- Day 単位での並列／部分実行 (`--day N` 機能の活用拡張)
- dry-run の強化 (mock LLM レスポンスでパイプライン構造のみ検証)
- 1 Day だけのキャッシュ resume

これらを同じ design.md で比較検討しようとするとスコープが大幅に拡張するため、
**本タスクは一旦クローズ** とし、後続で広いスコープの調査タスクを別途立ち上げる。

### 後続タスク（推奨）

- タスク名候補: `tuning-rotation-throughput` または `prompt-iter-velocity`
- 目的: プロンプトチューニング回転率を上げるための ROI 比較とボトルネック特定
- 入口: ボトルネック計測（現状 7 Day 生成の所要時間内訳・retry 頻度・同一入力での再生成頻度）
- 候補手段の比較対象に Best-of-N 並列化を含める（本 design.md の Option B/C/D 分析を参考資料として再利用）
- ブランチ命名: `feat/...` または `prompt/...` を選択（手段により変動）

### リスク / トレードオフ

並列化案の比較は「並列化アプローチの選択肢」節 (Option B/C/D) を後続タスクで参照すること。
