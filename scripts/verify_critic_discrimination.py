"""Critic の弁別力を検証するスクリプト。

修正前後で以下を比較する:
1. Layer 1/2 のスコア分散 (標準偏差)
2. 最終スコアのスコア分散
3. 各軸のスコアレンジ (max - min)

判定基準:
- L1/L2 の標準偏差 > 0.3 (修正前は 0.0)
- 最終スコアのレンジ >= 2 (修正前は 1)

使い方:
    python scripts/verify_critic_discrimination.py output/generation_log.json
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def _extract_layer_scores(
    records: list[dict[str, object]],
    layer_key: str,
) -> dict[str, list[float]]:
    """レコードから指定レイヤーの各軸スコアを抽出する。"""
    axes: dict[str, list[float]] = {
        "temporal_consistency": [],
        "emotional_plausibility": [],
        "persona_deviation": [],
    }
    for record in records:
        critic_results = record.get("critic_results")
        if not isinstance(critic_results, list) or not critic_results:
            continue
        last_result = critic_results[-1]
        if not isinstance(last_result, dict):
            continue
        layer = last_result.get(layer_key)
        if not isinstance(layer, dict):
            continue
        for axis in axes:
            val = layer.get(axis)
            if isinstance(val, (int, float)):
                axes[axis].append(float(val))
    return axes


def _extract_final_scores(
    records: list[dict[str, object]],
) -> dict[str, list[int]]:
    """レコードから最終スコアの各軸スコアを抽出する。"""
    axes: dict[str, list[int]] = {
        "temporal_consistency": [],
        "emotional_plausibility": [],
        "persona_deviation": [],
    }
    for record in records:
        scores = record.get("critic_scores")
        if not isinstance(scores, list) or not scores:
            continue
        last_score = scores[-1]
        if not isinstance(last_score, dict):
            continue
        for axis in axes:
            val = last_score.get(axis)
            if isinstance(val, int):
                axes[axis].append(val)
    return axes


def main(log_path: str) -> None:
    """メイン処理。"""
    path = Path(log_path)
    if not path.exists():
        print(f"Error: {log_path} が見つかりません")
        sys.exit(1)

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    if not records:
        print("Error: records が空です")
        sys.exit(1)

    print(f"=== Critic 弁別力検証: {len(records)} Days ===\n")

    # Layer 1/2 のスコア分散
    for layer_name, layer_key in [
        ("Layer 1 (RuleBased)", "rule_based"),
        ("Layer 2 (Statistical)", "statistical"),
        ("Layer 3 (LLMJudge)", "llm_judge"),
    ]:
        scores = _extract_layer_scores(records, layer_key)
        print(f"--- {layer_name} ---")
        for axis, values in scores.items():
            if len(values) >= 2:
                std = statistics.stdev(values)
                rng = max(values) - min(values)
                print(f"  {axis}: values={[round(v, 1) for v in values]}")
                print(f"    std={std:.3f}, range={rng:.1f}")
            else:
                print(f"  {axis}: データ不足 ({len(values)} records)")
        print()

    # 最終スコアの分散
    final_scores = _extract_final_scores(records)
    print("--- Final Score ---")
    all_ok = True
    for axis, values in final_scores.items():
        if len(values) >= 2:
            std = statistics.stdev(values)
            rng = max(values) - min(values)
            print(f"  {axis}: values={values}")
            print(f"    std={std:.3f}, range={rng}")
        else:
            print(f"  {axis}: データ不足 ({len(values)} records)")

    # 判定
    print("\n=== 判定 ===")
    for layer_name, layer_key in [
        ("L1", "rule_based"),
        ("L2", "statistical"),
    ]:
        scores = _extract_layer_scores(records, layer_key)
        stds = []
        for values in scores.values():
            if len(values) >= 2:
                stds.append(statistics.stdev(values))
        avg_std = statistics.mean(stds) if stds else 0.0
        status = "PASS" if avg_std > 0.3 else "FAIL"
        print(f"  {layer_name} 平均標準偏差: {avg_std:.3f} (目標 > 0.3) [{status}]")
        if status == "FAIL":
            all_ok = False

    for axis, values in final_scores.items():
        if len(values) >= 2:
            rng = max(values) - min(values)
            status = "PASS" if rng >= 2 else "FAIL"
            print(f"  Final {axis} レンジ: {rng} (目標 >= 2) [{status}]")
            if status == "FAIL":
                all_ok = False

    print()
    if all_ok:
        print("結果: 全ての判定基準を満たしています。")
    else:
        print("結果: 一部の判定基準を満たしていません。")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <generation_log.json>")
        sys.exit(1)
    main(sys.argv[1])
