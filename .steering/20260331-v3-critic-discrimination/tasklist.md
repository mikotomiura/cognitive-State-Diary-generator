# タスクリスト: v3→v4 Critic 弁別力改善

## 実装タスク
- [x] Task 1: `_BASE_SCORE` 3.5→2.5 (v3)
- [x] Task 2: Critic 重み 0.35/0.30/0.35 → 0.40/0.35/0.25 (v3)
- [x] Task 3: Prompt_Generator.md 余韻セクション Step 1-2-3 化 (v3)
- [x] 改善A: `_MAX_SCORE_ADJUSTMENT` 1→0 (v4)
- [x] 改善B: L1 ボーナス段階化 — watashi/ellipsis/char_count/overlap/deviation (v4)
- [x] 改善C: L2 ボーナス段階化 — punct/sentence_count/avg_len/question/deviation (v4)

## テスト・検証タスク
- [x] テスト期待値更新 (v3 + v4)
- [x] pytest 全 383 テスト pass
- [x] mypy strict pass
- [x] ruff check pass
- [x] 検証スクリプト修正 (critic_log.jsonl 対応)
- [x] パイプライン実行・検証

## 結果サマリ

| 指標 | v2 | v3 | v4 | 改善 |
|---|---|---|---|---|
| L1 avg std | 0.000 | 0.408 | **0.653** | ✓ |
| L2 avg std | 0.000 | 0.285 | **0.399** | ✓ |
| T range | 1→0 | 0 | **1** | +1 |
| E range | 1 | 1 | **1** | ± |
| P range | 0 | 0 | **1** | +1 |
| Unique patterns | 2 | 2 | **5** | ×2.5 |
| Retries | 1 | 3 | 1 | 安定 |
| Fallbacks | 0 | 0 | 0 | ✓ |
