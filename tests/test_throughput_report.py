"""tests/test_throughput_report.py -- scripts/throughput_report.py のテスト。

AAA パターンで集計関数とレポート出力の動作を検証する。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# scripts/ を import path に追加
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from throughput_report import (  # noqa: E402
    _get_records,
    _load_log,
    _phase_totals,
    _retry_distribution,
    _retry_lift,
    _score_total,
    generate_report,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_record(
    *,
    day: int,
    p1: int = 1000,
    p2: int = 2000,
    p3: int = 500,
    retry: int = 0,
    fallback: bool = False,
    scores: list[dict[str, int]] | None = None,
) -> dict[str, Any]:
    """テスト用の最小 record を構築する。"""
    return {
        "day": day,
        "phase1_duration_ms": p1,
        "phase2_duration_ms": p2,
        "phase3_duration_ms": p3,
        "retry_count": retry,
        "fallback_used": fallback,
        "critic_scores": scores or [{"temporal_consistency": 4, "emotional_plausibility": 4, "persona_deviation": 4}],
    }


@pytest.fixture()
def sample_log() -> dict[str, Any]:
    """3 Day 分の最小 PipelineLog 相当辞書を返す。"""
    return {
        "executed_at": "2026-05-01T12:00:00Z",
        "total_api_calls": 9,
        "total_retries": 2,
        "total_fallbacks": 0,
        # SHA256 (本番は 64 文字) を模擬。表示時に [:8] で切り詰められる
        "prompt_hashes": {
            "Prompt_Generator.md": "aaaaaaaa" + "11" * 28,
            "Prompt_Critic.md": "bbbbbbbb" + "22" * 28,
        },
        "records": [
            _make_record(day=1, p1=1000, p2=3000, p3=800, retry=0),
            _make_record(
                day=2,
                p1=1200,
                p2=4500,
                p3=2000,
                retry=1,
                scores=[
                    {"temporal_consistency": 3, "emotional_plausibility": 3, "persona_deviation": 3},
                    {"temporal_consistency": 4, "emotional_plausibility": 4, "persona_deviation": 4},
                ],
            ),
            _make_record(
                day=3,
                p1=1100,
                p2=3500,
                p3=900,
                retry=1,
                fallback=True,
                scores=[
                    {"temporal_consistency": 4, "emotional_plausibility": 4, "persona_deviation": 4},
                    {"temporal_consistency": 3, "emotional_plausibility": 4, "persona_deviation": 4},
                ],
            ),
        ],
    }


@pytest.fixture()
def sample_log_path(tmp_path: Path, sample_log: dict[str, Any]) -> Path:
    """sample_log を一時ファイルに書き出してパスを返す。"""
    p = tmp_path / "generation_log.json"
    p.write_text(json.dumps(sample_log, ensure_ascii=False), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestLoadLog:
    def test_valid_json_returns_dict(self, sample_log_path: Path, sample_log: dict[str, Any]) -> None:
        # Act
        loaded = _load_log(sample_log_path)
        # Assert
        assert loaded == sample_log

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        # Arrange
        missing = tmp_path / "nope.json"
        # Act / Assert
        with pytest.raises(OSError):
            _load_log(missing)

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        # Arrange
        p = tmp_path / "broken.json"
        p.write_text("{not json", encoding="utf-8")
        # Act / Assert
        with pytest.raises(json.JSONDecodeError):
            _load_log(p)


class TestRecords:
    def test_returns_records_list(self, sample_log: dict[str, Any]) -> None:
        # Act
        rs = _get_records(sample_log)
        # Assert
        assert len(rs) == 3
        assert rs[0]["day"] == 1

    def test_empty_when_missing(self) -> None:
        # Act
        rs = _get_records({})
        # Assert
        assert rs == []


class TestPhaseTotals:
    def test_sums_each_phase(self, sample_log: dict[str, Any]) -> None:
        # Act
        p1, p2, p3 = _phase_totals(_get_records(sample_log))
        # Assert
        assert p1 == 1000 + 1200 + 1100
        assert p2 == 3000 + 4500 + 3500
        assert p3 == 800 + 2000 + 900

    def test_zero_for_empty_records(self) -> None:
        # Act
        p1, p2, p3 = _phase_totals([])
        # Assert
        assert (p1, p2, p3) == (0, 0, 0)

    def test_handles_missing_keys(self) -> None:
        # Arrange
        records = [{"day": 1}]
        # Act
        p1, p2, p3 = _phase_totals(records)
        # Assert
        assert (p1, p2, p3) == (0, 0, 0)


class TestRetryDistribution:
    def test_counts_per_retry_level(self, sample_log: dict[str, Any]) -> None:
        # Act
        dist = _retry_distribution(_get_records(sample_log))
        # Assert
        assert dist == {0: 1, 1: 2}

    def test_empty_for_no_records(self) -> None:
        # Act
        dist = _retry_distribution([])
        # Assert
        assert dist == {}


class TestScoreTotal:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            ({"temporal_consistency": 4, "emotional_plausibility": 4, "persona_deviation": 4}, 12),
            ({"temporal_consistency": 1, "emotional_plausibility": 2, "persona_deviation": 3}, 6),
            ({}, 0),
        ],
    )
    def test_sums_three_dimensions(self, score: dict[str, int], expected: int) -> None:
        # Act
        actual = _score_total(score)
        # Assert
        assert actual == expected


class TestRetryLift:
    def test_returns_first_and_last_when_multiple(self, sample_log: dict[str, Any]) -> None:
        # Arrange
        record = _get_records(sample_log)[1]  # Day 2: 2 attempts, 9 -> 12
        # Act
        lift = _retry_lift(record)
        # Assert
        assert lift == (9, 12)

    def test_returns_none_when_single_attempt(self, sample_log: dict[str, Any]) -> None:
        # Arrange
        record = _get_records(sample_log)[0]  # Day 1: 1 attempt
        # Act
        lift = _retry_lift(record)
        # Assert
        assert lift is None

    def test_returns_none_when_no_scores(self) -> None:
        # Act
        lift = _retry_lift({"critic_scores": []})
        # Assert
        assert lift is None


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_single_run_outputs_report(
        self,
        sample_log_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Act
        ok = generate_report([sample_log_path])
        captured = capsys.readouterr().out
        # Assert
        assert ok is True
        assert "CSDG スループット計測レポート" in captured
        assert "Phase 2:" in captured
        assert "観測サマリ" in captured
        # Day 別行が出ている
        assert "Day" in captured

    def test_multi_run_includes_comparison_and_hash_diff(
        self,
        tmp_path: Path,
        sample_log: dict[str, Any],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Arrange: 2 ラン (Generator のハッシュだけ差分)
        log_a = sample_log
        log_b = json.loads(json.dumps(sample_log))
        log_b["prompt_hashes"]["Prompt_Generator.md"] = "cccccccc" + "33" * 28
        path_a = tmp_path / "run_a/generation_log.json"
        path_b = tmp_path / "run_b/generation_log.json"
        path_a.parent.mkdir()
        path_b.parent.mkdir()
        path_a.write_text(json.dumps(log_a), encoding="utf-8")
        path_b.write_text(json.dumps(log_b), encoding="utf-8")
        # Act
        ok = generate_report([path_a, path_b])
        captured = capsys.readouterr().out
        # Assert
        assert ok is True
        assert "Run 横並び比較" in captured
        assert "Prompt Hash 比較" in captured
        # Generator.md は差分マーク *
        assert "Prompt_Generator.md" in captured
        # Critic.md は同一マーク =
        assert "Prompt_Critic.md" in captured

    def test_unreadable_file_returns_false(
        self,
        tmp_path: Path,
        sample_log_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Arrange
        broken = tmp_path / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        # Act
        ok = generate_report([sample_log_path, broken])
        captured = capsys.readouterr()
        # Assert
        assert ok is False
        assert "を読み込めません" in captured.err

    def test_all_unreadable_returns_false(
        self,
        tmp_path: Path,
    ) -> None:
        # Arrange
        broken = tmp_path / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        # Act
        ok = generate_report([broken])
        # Assert
        assert ok is False
