"""CSDG スループット計測レポート生成スクリプト。

generation_log.json を 1 つ以上解析し、Phase 1/2/3 の所要時間内訳・retry 分布・
retry スコア lift・プロンプトハッシュ比較を集計してレポートとして出力する。

「プロンプトチューニング回転率」のボトルネック特定に用いる。

Usage:
    # 単一ラン
    python scripts/throughput_report.py output/generation_log.json

    # 複数ラン比較 (prompt_hash 比較表が追加される)
    python scripts/throughput_report.py output/generation_log.json output_archive_*/generation_log.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any  # JSON 構造は外部ファイル依存で静的型付け不能なため Any を使用

# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------


def _load_log(path: Path) -> dict[str, Any]:
    """generation_log.json を読み込んで辞書として返す。"""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _get_records(log: dict[str, Any]) -> list[dict[str, Any]]:
    """PipelineLog からレコード一覧を取得する。"""
    return log.get("records", [])  # type: ignore[no-any-return]


def _get_executed_at(log: dict[str, Any]) -> str:
    """実行日時文字列を返す。"""
    if "executed_at" in log:
        return str(log["executed_at"])
    return "(unknown)"


def _phase_totals(records: list[dict[str, Any]]) -> tuple[int, int, int]:
    """Phase 1/2/3 の合計時間 (ms) を返す。"""
    p1 = sum(int(r.get("phase1_duration_ms", 0)) for r in records)
    p2 = sum(int(r.get("phase2_duration_ms", 0)) for r in records)
    p3 = sum(int(r.get("phase3_duration_ms", 0)) for r in records)
    return p1, p2, p3


def _retry_distribution(records: list[dict[str, Any]]) -> dict[int, int]:
    """retry_count の分布 (retry 回数 -> Day 数) を返す。"""
    dist: dict[int, int] = {}
    for r in records:
        n = int(r.get("retry_count", 0))
        dist[n] = dist.get(n, 0) + 1
    return dict(sorted(dist.items()))


def _score_total(score: dict[str, Any]) -> int:
    """Critic スコア辞書の合計 (temporal + emotional + persona) を返す。"""
    return (
        int(score.get("temporal_consistency", 0))
        + int(score.get("emotional_plausibility", 0))
        + int(score.get("persona_deviation", 0))
    )


def _retry_lift(record: dict[str, Any]) -> tuple[int, int] | None:
    """retry のスコア lift (初回合計, 最終合計) を返す。retry が無ければ None。"""
    scores = record.get("critic_scores", [])
    if not isinstance(scores, list) or len(scores) < 2:
        return None
    first = scores[0]
    last = scores[-1]
    if not isinstance(first, dict) or not isinstance(last, dict):
        return None
    return _score_total(first), _score_total(last)


# ---------------------------------------------------------------------------
# Per-run report
# ---------------------------------------------------------------------------


def _print_run_summary(label: str, log: dict[str, Any]) -> None:
    """単一ランのスループットサマリを出力する。"""
    records = _get_records(log)
    n_days = len(records)
    p1, p2, p3 = _phase_totals(records)
    total = p1 + p2 + p3
    total_retries = sum(int(r.get("retry_count", 0)) for r in records)
    total_fallbacks = sum(1 for r in records if r.get("fallback_used"))
    api_calls = log.get("total_api_calls", "N/A")
    executed = _get_executed_at(log)

    print(f"=== Run: {label} ===")
    print(f"  実行日時:   {executed}")
    print(f"  Days:       {n_days}")
    print(f"  Total:      {total / 1000:.1f}s")
    if total > 0:
        print(f"  Phase 1:    {p1 / 1000:.1f}s ({p1 / total * 100:.1f}%)")
        print(f"  Phase 2:    {p2 / 1000:.1f}s ({p2 / total * 100:.1f}%)")
        print(f"  Phase 3:    {p3 / 1000:.1f}s ({p3 / total * 100:.1f}%)")
    else:
        print("  Phase 1/2/3: (no timing data)")
    print(f"  retries:    {total_retries}")
    print(f"  fallbacks:  {total_fallbacks}")
    print(f"  api_calls:  {api_calls}")
    print()

    # Day 別タイミング
    print("  --- Day 別タイミング ---")
    print(f"  {'Day':>4} {'P1(ms)':>8} {'P2(ms)':>8} {'P3(ms)':>8} {'retry':>6} {'lift':>10} {'fb':>4}")
    for r in records:
        day = r.get("day", "?")
        p1d = int(r.get("phase1_duration_ms", 0))
        p2d = int(r.get("phase2_duration_ms", 0))
        p3d = int(r.get("phase3_duration_ms", 0))
        retry = int(r.get("retry_count", 0))
        fb = "yes" if r.get("fallback_used") else "no"
        lift = _retry_lift(r)
        lift_str = f"{lift[0]}->{lift[1]}" if lift is not None else "-"
        print(f"  {day:>4} {p1d:>8} {p2d:>8} {p3d:>8} {retry:>6} {lift_str:>10} {fb:>4}")
    print()

    # retry 分布
    dist = _retry_distribution(records)
    print("  --- retry 分布 ---")
    for n_retry, n_day in dist.items():
        print(f"  retry={n_retry}: {n_day} day(s)")
    print()


# ---------------------------------------------------------------------------
# Multi-run comparison
# ---------------------------------------------------------------------------


def _print_prompt_hash_diff(labels: list[str], logs: list[dict[str, Any]]) -> None:
    """複数ランの prompt_hashes を横並びで比較する。"""
    if len(logs) < 2:
        return

    all_keys: set[str] = set()
    for log in logs:
        hashes = log.get("prompt_hashes", {})
        if isinstance(hashes, dict):
            all_keys.update(hashes.keys())

    if not all_keys:
        return

    print("=== Prompt Hash 比較 ===")
    name_width = max(len(k) for k in all_keys)
    header = f"  {'prompt':<{name_width}}  " + "  ".join(f"{lbl:<8}" for lbl in labels)
    print(header)
    for key in sorted(all_keys):
        cells: list[str] = []
        for log in logs:
            hashes = log.get("prompt_hashes", {})
            h = hashes.get(key, "") if isinstance(hashes, dict) else ""
            cells.append(h[:8] if h else "(none)  ")
        # 全ラン同一かどうかのマーク
        non_empty = [c for c in cells if c != "(none)  "]
        same = len(set(non_empty)) <= 1
        mark = "=" if same else "*"
        print(f"  {key:<{name_width}}  " + "  ".join(cells) + f"  [{mark}]")
    print("  (= 全ラン同一 / * 差分あり)")
    print()


def _print_run_comparison_table(labels: list[str], logs: list[dict[str, Any]]) -> None:
    """複数ランの主要指標を横並び比較する。"""
    if len(logs) < 2:
        return

    print("=== Run 横並び比較 ===")
    print(f"  {'metric':<14}  " + "  ".join(f"{lbl:>10}" for lbl in labels))

    rows: list[tuple[str, list[str]]] = []
    for log in logs:
        records = _get_records(log)
        p1, p2, p3 = _phase_totals(records)
        total = p1 + p2 + p3
        retries = sum(int(r.get("retry_count", 0)) for r in records)
        fb = sum(1 for r in records if r.get("fallback_used"))
        rows.append(
            (
                "",
                [
                    str(len(records)),
                    f"{total / 1000:.1f}s",
                    f"{p1 / 1000:.1f}s",
                    f"{p2 / 1000:.1f}s",
                    f"{p3 / 1000:.1f}s",
                    f"{p2 / total * 100:.1f}%" if total > 0 else "-",
                    str(retries),
                    str(fb),
                ],
            )
        )

    metrics = ["days", "total", "phase1", "phase2", "phase3", "P2 share", "retries", "fallbacks"]
    for i, m in enumerate(metrics):
        cells = [row[1][i] for row in rows]
        print(f"  {m:<14}  " + "  ".join(f"{c:>10}" for c in cells))
    print()


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------


def _observations(labels: list[str], logs: list[dict[str, Any]]) -> list[str]:
    """簡易な所見テキストを生成する。"""
    notes: list[str] = []
    if not logs:
        return notes

    # Phase 2 share の平均
    shares: list[float] = []
    retry_rates: list[float] = []
    for log in logs:
        records = _get_records(log)
        if not records:
            continue
        p1, p2, p3 = _phase_totals(records)
        total = p1 + p2 + p3
        if total > 0:
            shares.append(p2 / total * 100)
        retries = sum(int(r.get("retry_count", 0)) for r in records)
        retry_rates.append(retries / len(records))

    if shares:
        avg_share = sum(shares) / len(shares)
        notes.append(
            f"Phase 2 (Content Generation) が時間の {min(shares):.0f}-{max(shares):.0f}% "
            f"(平均 {avg_share:.0f}%) を占める -> 主ボトルネック",
        )
    if retry_rates:
        avg_rate = sum(retry_rates) / len(retry_rates)
        notes.append(
            f"retry 率は Day あたり {min(retry_rates):.2f}-{max(retry_rates):.2f} "
            f"(平均 {avg_rate:.2f})。0 retry のランは観測されない傾向"
        )

    # retry lift 集計
    lifts: list[tuple[int, int]] = []
    for log in logs:
        for r in _get_records(log):
            lift = _retry_lift(r)
            if lift is not None:
                lifts.append(lift)
    if lifts:
        improved = sum(1 for first, last in lifts if last > first)
        unchanged = sum(1 for first, last in lifts if last == first)
        regressed = sum(1 for first, last in lifts if last < first)
        notes.append(
            f"retry の合計スコア lift: 改善 {improved} / 同点 {unchanged} / 悪化 {regressed} "
            f"(retry 経由でスコアが必ずしも上がっていないケースが {unchanged + regressed} 件)"
        )

    # prompt_hash 同一ランの組
    if len(logs) >= 2:
        gen_hashes = []
        for log in logs:
            hashes = log.get("prompt_hashes", {})
            gen_hashes.append(hashes.get("Prompt_Generator.md", "") if isinstance(hashes, dict) else "")
        unique_gen = {h for h in gen_hashes if h}
        if 1 < len(unique_gen) < len(gen_hashes):
            notes.append(
                "Prompt_Generator.md のハッシュが run 間で重複あり -> 同一プロンプトでの再実行が起きている "
                "(LLM レスポンスキャッシュの効果余地あり)"
            )
        elif len(unique_gen) == len(gen_hashes) and len(gen_hashes) > 1:
            notes.append(
                "Prompt_Generator.md は全 run で異なる -> プロンプト編集サイクルが回っており、"
                "キャッシュより固定 seed / 並列化のほうが効きやすい局面"
            )

    return notes


def _print_observations(labels: list[str], logs: list[dict[str, Any]]) -> None:
    """観測サマリを整形して出力する。"""
    notes = _observations(labels, logs)
    print("=== 観測サマリ ===")
    if not notes:
        print("  (所見なし)")
    for i, note in enumerate(notes, 1):
        print(f"  [{i}] {note}")
    print()


# ---------------------------------------------------------------------------
# Public report API
# ---------------------------------------------------------------------------


def generate_report(paths: list[Path]) -> bool:
    """1 つ以上の generation_log.json を解析し、レポートを stdout に出力する。

    読み込み失敗 (OSError / json.JSONDecodeError) は内部でキャッチして stderr に
    エラーメッセージを出し、残りのファイル処理を続ける (Self-Healing)。

    Args:
        paths: 解析対象の generation_log.json パスのリスト。1 つ以上必須。

    Returns:
        全パスが正常に処理された場合は True。読み込み失敗が 1 件以上あれば False
        (ただし読み込めたファイルだけでもレポートは出力される)。読み込み可能な
        ファイルが 1 件もなければ False を返してレポート出力をスキップする。
    """
    logs: list[dict[str, Any]] = []
    labels: list[str] = []
    ok = True
    for path in paths:
        try:
            log = _load_log(path)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error: {path} を読み込めません: {exc}", file=sys.stderr)
            ok = False
            continue
        logs.append(log)
        labels.append(path.parent.name or path.name)

    if not logs:
        return False

    print("=== CSDG スループット計測レポート ===")
    print(f"対象 run 数: {len(logs)}")
    print()

    for label, log in zip(labels, logs, strict=True):
        _print_run_summary(label, log)

    _print_run_comparison_table(labels, logs)
    _print_prompt_hash_diff(labels, logs)
    _print_observations(labels, logs)

    return ok


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI エントリポイント。"""
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/throughput_report.py <generation_log.json> [<generation_log.json> ...]",
            file=sys.stderr,
        )
        sys.exit(2)

    paths = [Path(p) for p in sys.argv[1:]]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"Error: ファイルが見つかりません: {p}", file=sys.stderr)
        sys.exit(2)

    ok = generate_report(paths)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
