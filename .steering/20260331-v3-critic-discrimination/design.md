# 設計: v4 Critic 弁別力改善

## v3 の残存問題

v3 で `_BASE_SCORE=2.5` + 重み `0.40/0.35/0.25` に変更したが、
final score が 3 に圧縮される問題が解決されなかった。

### 根本原因（2つ）

1. **round() 圧縮**: 加重平均 21 値中 17 値 (81%) が [2.5, 3.5] に集中 → round=3
2. **コンセンサス補正の逆効果**: `_MAX_SCORE_ADJUSTMENT=1` により、
   - Day 3 emotional: WA=2.35→round(2) が consensus→3 に引き上げ
   - Day 5 persona: WA=3.625→round(4) が consensus→3 に引き下げ

### L1/L2 ボーナス構造の問題

| 軸 | L1 max | L2 max | 実測 range | 問題 |
|---|---|---|---|---|
| temporal | 3.5 | 3.5 | 0.5 | ボーナス幅 ±0.5 が round() 閾値以下 |
| emotional | 4.0 | 4.0 | 2.0 | deviation で自然に分離（唯一良好） |
| persona | 3.5 | 3.5 | 0.5 | 同上 |

## 実装アプローチ

### 改善 A: コンセンサス安全上限の無効化（最高インパクト・最低リスク）

`_MAX_SCORE_ADJUSTMENT = 1` → `0`

これにより consensus amplification の計算は残るが、
round(weighted) と round(amplified) の差がある場合に
round(weighted) が常に採用される。

単独効果: E range 1→2, P range 0→1

### 改善 B: L1 ボーナスの段階化（medium インパクト）

現行の flat +0.5 ボーナスを、sweet spot / acceptable / penalty の3段階に拡張。

#### persona_deviation

```
watashi_count:
  [4, 6] → +1.0 (sweet spot)
  [2, 8] → +0.5 (acceptable)
  > 8    → -1.0 (overuse penalty) ← 新規追加
  else   → +0.0

ellipsis_count:
  [2, 3] → +1.0 (sweet spot)
  {1, 4} → +0.5 (acceptable)
  else   → +0.0
```

新 L1 persona range: 1.5-4.5 (現行 2.5-3.5)

#### temporal_consistency

```
char_count:
  [1000, 1200] → +1.0 (sweet spot)
  [1000, 1400] → +0.5 (acceptable)
  else         → +0.0

trigram_overlap:
  < 0.10 → +1.0 (very different)
  < 0.15 → +0.5 (moderately different)
  else   → +0.0
```

新 L1 temporal range: 2.5-4.5 (現行 2.5-3.5)

#### emotional_plausibility

```
rule_max_deviation >= 0.12: -0.5 → -1.0 (penalty 増強)
```

### 改善 C: L2 ボーナスの段階化（medium インパクト）

#### temporal_consistency

```
punct_ratio:
  [0.070, 0.080] → +1.0 (sweet)
  [0.060, 0.090] → +0.5 (acceptable)
  else           → +0.0

sentence_count:
  [35, 45] → +1.0 (sweet)
  [30, 50] → +0.5 (acceptable)
  else     → +0.0
```

#### persona_deviation

```
avg_sentence_len:
  [25, 30] → +1.0 (sweet)
  [20, 35] → +0.5 (acceptable)
  else     → +0.0

question_ratio:
  [0.06, 0.10] → +1.0 (sweet)
  [0.05, 0.15] → +0.5 (acceptable)
  else         → +0.0
```

#### emotional_plausibility

```
max_deviation 0.25-0.40: -0.5 → -1.0 (penalty 増強)
```

## シミュレーション結果（実データ）

v3 の実生成データ (7日間) に対して改善 A+B+C を適用した結果:

| Day | v3 (T/E/P) | v4 (T/E/P) | reject |
|-----|-----------|-----------|--------|
| 1 | 3/3/3 | 4/3/3 | |
| 2 | 3/3/3 | 4/3/4 | |
| 3 | 3/3/3 | 4/2/3 | ✓ E<3 |
| 4 | 3/4/3 | 4/4/4 | |
| 5 | 3/3/3 | 4/3/4 | |
| 6 | 3/3/3 | 4/3/4 | |
| 7 | 3/4/3 | 3/4/3 | |

| 指標 | v3 | v4 | 改善 |
|---|---|---|---|
| T range | 0 | 1 | +1 |
| E range | 1 | **2** | +1 ✓ |
| P range | 0 | 1 | +1 |
| Unique patterns | 2 | **5** | ×2.5 |
| Reject trigger | 0 | 1 | Critic が弁別を実行 |

## 変更対象ファイル

| ファイル | 変更内容 |
|---|---|
| csdg/engine/critic.py | 改善 A + B + C (ボーナス段階化 + 定数変更) |
| tests/test_critic.py | 期待値更新 |
| scripts/verify_critic_discrimination.py | critic_log.jsonl からのレイヤースコア抽出修正 |

## 変更しない箇所

- `_BASE_SCORE = 2.5` (v3 で変更済み、維持)
- 重み `0.40/0.35/0.25` (v3 で変更済み、維持)
- `_CONSENSUS_AMPLIFICATION = 0.5` (計算は残る、MAX_ADJ=0 で効果を制限)
- 余韻テンプレート検出、哲学者カウンター、場面構造パターン検出
- Prompt_Generator.md, Prompt_Critic.md
