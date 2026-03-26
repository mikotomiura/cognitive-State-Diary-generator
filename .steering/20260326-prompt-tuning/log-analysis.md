# log-analyzer 分析結果: チューニング後パイプライン

## パイプライン健全性

| 指標 | 値 | 判定 |
|------|-----|------|
| 完了Day数 | 7/7 (100%) | ✅ |
| フォールバック | 0/7 (0%) | ✅ |
| 総リトライ | 0 | ✅ |
| 総処理時間 | 217秒 (3分37秒) | ✅ |
| 総API呼び出し | 21回 (3.0/日) | ✅ |

## CriticScore

| Day | temporal | emotional | persona | Total |
|-----|----------|-----------|---------|-------|
| 1 | 4 | 4 | 5 | 13 |
| 2 | 4 | 4 | 5 | 13 |
| 3 | 5 | 4 | 5 | 14 |
| 4 | 5 | 4 | 5 | 14 |
| 5 | 5 | 4 | 5 | 14 |
| 6 | 5 | 5 | 5 | 15 |
| 7 | 5 | 4 | 5 | 14 |

- persona_deviation: 全日5.0 (完璧)
- temporal_consistency: Day 1-2 が 4、Day 3-7 が 5 (上昇トレンド)
- emotional_plausibility: 6/7日が 4、Day 6 のみ 5 (天井感あり)

## 検出された懸念事項

### 高優先度
1. **fatigue が負値** — Day 6 後に -0.0002、Day 7 後に -0.069。意味的に疲労が負であることは不自然な可能性。clamp の下限が -1.0 ではなく 0.0 であるべきか要検討。

### 中優先度
2. **Day 1 motivation の逆転** — expected_delta +0.080 に対し actual -0.038 (方向が逆)。State Update が unresolved_issue を重視しすぎている可能性。
3. **emotional_plausibility の天井** — 6/7日が 4。Critic のスコア5の基準が高いか、Generator の感情表現に改善余地。
4. **unresolved_issue が7日間不変** — Day 4-7 で同一テキスト。回復イベントを経ても部分的に解消/精緻化されていない。

### 低優先度
5. **Day 7 stress の under-correction** — expected -0.150 に対し actual -0.019 (deviation +0.131、最大)。
6. **リトライが1回も発生しない** — Critic の閾値が緩すぎる可能性。ストレステストで確認推奨。

## 処理時間ボトルネック

- Phase 2 (日記生成) が平均 22.4秒で全体の72%を占める (想定通り)
- Phase 3 (Critic) は 1.8-2.4秒で安定
- Day 4 が最長 (35.3秒) — 高 emotional_impact による複雑な生成
