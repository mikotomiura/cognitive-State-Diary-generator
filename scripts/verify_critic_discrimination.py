"""Critic の弁別力を検証するスクリプト。

修正前後で以下を比較する:
1. Layer 1/2 のスコア分散 (標準偏差)
2. 最終スコアのスコア分散
3. 各軸のスコアレンジ (max - min)
4. 加重平均のレンジ

判定基準:
- L1/L2 の標準偏差 > 0.3 (修正前は 0.0)
- 最終スコアのレンジ >= 2 (修正前は 1)
- 加重平均のレンジ > 1.5

使い方:
    python scripts/verify_critic_discrimination.py output/generation_log.json
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def _load_critic_log(log_dir: Path, num_days: int) -> list[dict[str, object]]:
    """critic_log.jsonl から最新 num_days 件のエントリを読み込む。"""
    critic_path = log_dir / "critic_log.jsonl"
    if not critic_path.exists():
        return []
    entries: list[dict[str, object]] = []
    with critic_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    # 最新の num_days 件を返す
    return entries[-num_days:] if len(entries) >= num_days else entries


def _extract_layer_scores_from_critic_log(
    entries: list[dict[str, object]],
    layer_key: str,
) -> dict[str, list[float]]:
    """critic_log.jsonl のエントリから指定レイヤーの各軸スコアを抽出する。"""
    axes: dict[str, list[float]] = {
        "temporal_consistency": [],
        "emotional_plausibility": [],
        "persona_deviation": [],
    }
    for entry in entries:
        scores = entry.get("scores")
        if not isinstance(scores, dict):
            continue
        layer = scores.get(layer_key)
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
    """generation_log.json から最終スコアの各軸スコアを抽出する。"""
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

    num_days = len(records)
    print(f"=== Critic 弁別力検証: {num_days} Days ===\n")

    # critic_log.jsonl からレイヤースコアを抽出
    log_dir = path.parent
    critic_entries = _load_critic_log(log_dir, num_days)

    if critic_entries:
        print(f"(critic_log.jsonl から {len(critic_entries)} エントリを読み込み)\n")

    # Layer 1/2/3 のスコア分散
    for layer_name, layer_key in [
        ("Layer 1 (RuleBased)", "rule_based"),
        ("Layer 2 (Statistical)", "statistical"),
        ("Layer 3 (LLMJudge)", "llm_judge"),
    ]:
        scores = _extract_layer_scores_from_critic_log(critic_entries, layer_key)
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

    # 加重平均 range
    weights = {"rule_based": 0.40, "statistical": 0.35, "llm_judge": 0.25}
    layer_keys = ["rule_based", "statistical", "llm_judge"]
    all_layer_scores: dict[str, dict[str, list[float]]] = {}
    for layer_key in layer_keys:
        all_layer_scores[layer_key] = _extract_layer_scores_from_critic_log(critic_entries, layer_key)

    num_entries = len(critic_entries)
    weighted_avgs: list[float] = []
    for i in range(num_entries):
        day_scores: dict[str, float] = {}
        valid = True
        for axis in ["temporal_consistency", "emotional_plausibility", "persona_deviation"]:
            axis_weighted = 0.0
            for layer_key in layer_keys:
                vals = all_layer_scores[layer_key][axis]
                if i >= len(vals):
                    valid = False
                    break
                axis_weighted += weights[layer_key] * vals[i]
            if not valid:
                break
            day_scores[axis] = axis_weighted
        if valid and day_scores:
            avg = statistics.mean(day_scores.values())
            weighted_avgs.append(round(avg, 3))

    if weighted_avgs:
        wa_range = max(weighted_avgs) - min(weighted_avgs)
        print(f"\n--- Weighted Average (w={weights}) ---")
        print(f"  values={weighted_avgs}")
        print(f"  range={wa_range:.3f}")

    # 判定
    print("\n=== 判定 ===")
    for layer_name, layer_key in [
        ("L1", "rule_based"),
        ("L2", "statistical"),
    ]:
        scores = _extract_layer_scores_from_critic_log(critic_entries, layer_key)
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

    # 加重平均 range 判定
    if weighted_avgs:
        wa_range = max(weighted_avgs) - min(weighted_avgs)
        status = "PASS" if wa_range > 1.5 else "FAIL"
        print(f"  Weighted Avg レンジ: {wa_range:.3f} (目標 > 1.5) [{status}]")
        if status == "FAIL":
            all_ok = False

    # Unique patterns 判定
    unique_patterns = set()
    for record in records:
        scores_list = record.get("critic_scores")
        if isinstance(scores_list, list) and scores_list:
            last = scores_list[-1]
            if isinstance(last, dict):
                t = last.get("temporal_consistency", 0)
                e = last.get("emotional_plausibility", 0)
                p = last.get("persona_deviation", 0)
                unique_patterns.add((t, e, p))
    print(f"  Unique スコアパターン: {len(unique_patterns)} (目標 >= 3)")
    if len(unique_patterns) < 3:
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
