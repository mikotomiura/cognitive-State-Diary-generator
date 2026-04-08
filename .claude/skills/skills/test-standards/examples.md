# テスト実装例集

> CSDG プロジェクトのテスト実装パターン。

---

## 1. Pydantic モデルのバリデーションテスト

```python
import pytest
from pydantic import ValidationError
from csdg.schemas import CharacterState, DailyEvent, CriticScore


class TestCharacterStateClamp:
    """CharacterState の連続変数クランプのテスト。"""

    @pytest.mark.parametrize("field", ["fatigue", "motivation", "stress"])
    def test_clamp_upper(self, field: str) -> None:
        """各連続変数は1.0にクランプされる。"""
        kwargs = {
            "fatigue": 0.0, "motivation": 0.0, "stress": 0.0,
            "current_focus": "test", "growth_theme": "test",
            field: 1.5,
        }
        state = CharacterState(**kwargs)
        assert getattr(state, field) == 1.0

    @pytest.mark.parametrize("field", ["fatigue", "motivation", "stress"])
    def test_clamp_lower(self, field: str) -> None:
        """各連続変数は-1.0にクランプされる。"""
        kwargs = {
            "fatigue": 0.0, "motivation": 0.0, "stress": 0.0,
            "current_focus": "test", "growth_theme": "test",
            field: -2.0,
        }
        state = CharacterState(**kwargs)
        assert getattr(state, field) == -1.0

    @pytest.mark.parametrize("value", [-1.0, -0.5, 0.0, 0.5, 1.0])
    def test_within_range(self, value: float) -> None:
        """範囲内の値はそのまま保持される。"""
        state = CharacterState(
            fatigue=value, motivation=0.0, stress=0.0,
            current_focus="test", growth_theme="test",
        )
        assert state.fatigue == value


class TestCharacterStateMemoryBuffer:
    """CharacterState の memory_buffer サイズ制限テスト。"""

    def test_buffer_within_limit(self) -> None:
        """3件以下のバッファはそのまま保持される。"""
        state = CharacterState(
            fatigue=0.0, motivation=0.0, stress=0.0,
            current_focus="test", growth_theme="test",
            memory_buffer=["day1", "day2", "day3"],
        )
        assert len(state.memory_buffer) == 3

    def test_buffer_truncated(self) -> None:
        """4件以上のバッファは末尾3件に切り詰められる。"""
        state = CharacterState(
            fatigue=0.0, motivation=0.0, stress=0.0,
            current_focus="test", growth_theme="test",
            memory_buffer=["day1", "day2", "day3", "day4"],
        )
        assert state.memory_buffer == ["day2", "day3", "day4"]

    def test_empty_buffer(self) -> None:
        """空のバッファはそのまま保持される。"""
        state = CharacterState(
            fatigue=0.0, motivation=0.0, stress=0.0,
            current_focus="test", growth_theme="test",
        )
        assert state.memory_buffer == []
```

---

## 2. CriticScore の Pass/Reject 判定テスト

```python
class TestCriticJudge:
    """CriticScore の Pass/Reject 判定テスト。"""

    def test_all_pass(self) -> None:
        """全スコア3以上で Pass。"""
        score = CriticScore(
            temporal_consistency=4,
            emotional_plausibility=3,
            persona_deviation=5,
        )
        assert judge(score) is True

    def test_boundary_pass(self) -> None:
        """全スコアちょうど3で Pass（境界値）。"""
        score = CriticScore(
            temporal_consistency=3,
            emotional_plausibility=3,
            persona_deviation=3,
        )
        assert judge(score) is True

    @pytest.mark.parametrize("low_field", [
        "temporal_consistency",
        "emotional_plausibility",
        "persona_deviation",
    ])
    def test_single_reject(self, low_field: str) -> None:
        """1つでも3未満があれば Reject。"""
        kwargs = {
            "temporal_consistency": 4,
            "emotional_plausibility": 4,
            "persona_deviation": 4,
            low_field: 2,
            "reject_reason": "テスト理由",
            "revision_instruction": "テスト指示",
        }
        score = CriticScore(**kwargs)
        assert judge(score) is False
```

---

## 3. expected_delta と deviation の計算テスト

```python
class TestDeviationComputation:
    """Critic の定量検証ロジックのテスト。"""

    def test_positive_event(self) -> None:
        """positive イベントの expected_delta。"""
        event = DailyEvent(
            day=2, event_type="positive", domain="趣味",
            description="古書店で西田幾多郎の初版本を発見した",
            emotional_impact=0.6,
        )
        sensitivity = {"stress": -0.3, "motivation": 0.4, "fatigue": -0.2}
        expected = compute_expected_delta(event, sensitivity)

        assert expected["stress"] == pytest.approx(-0.18)
        assert expected["motivation"] == pytest.approx(0.24)
        assert expected["fatigue"] == pytest.approx(-0.12)

    def test_negative_event(self) -> None:
        """negative イベント（Day 4 ストレステスト）。"""
        event = DailyEvent(
            day=4, event_type="negative", domain="仕事",
            description="全社会議でAI自動化ロードマップが発表された",
            emotional_impact=-0.9,
        )
        sensitivity = {"stress": -0.3, "motivation": 0.4, "fatigue": -0.2}
        expected = compute_expected_delta(event, sensitivity)

        assert expected["stress"] == pytest.approx(0.27)
        assert expected["motivation"] == pytest.approx(-0.36)
        assert expected["fatigue"] == pytest.approx(0.18)
```

---

## 4. パイプラインのリトライテスト（モック使用）

```python
class TestPipelineRetry:
    """パイプラインのリトライ制御テスト。"""

    @pytest.mark.asyncio
    async def test_pass_on_first_attempt(self, mock_llm: LLMClient) -> None:
        """1回目で Pass する場合、リトライしない。"""
        mock_llm.generate_structured.return_value = CriticScore(
            temporal_consistency=4, emotional_plausibility=4, persona_deviation=5,
        )
        pipeline = PipelineRunner(config, Actor(mock_llm, config), Critic(mock_llm, config))
        record = await pipeline.run_single_day(event, initial_state, day=1)

        assert record.retry_count == 0
        assert record.fallback_used is False

    @pytest.mark.asyncio
    async def test_pass_on_retry(self, mock_llm: LLMClient) -> None:
        """Reject → リトライで Pass する場合。"""
        reject_score = CriticScore(
            temporal_consistency=2, emotional_plausibility=4, persona_deviation=4,
            reject_reason="時間的矛盾", revision_instruction="過去の記憶を参照して",
        )
        pass_score = CriticScore(
            temporal_consistency=4, emotional_plausibility=4, persona_deviation=4,
        )
        # 1回目Reject、2回目Pass
        mock_llm.generate_structured.side_effect = [reject_score, pass_score]

        pipeline = PipelineRunner(config, Actor(mock_llm, config), Critic(mock_llm, config))
        record = await pipeline.run_single_day(event, initial_state, day=1)

        assert record.retry_count == 1
        assert record.fallback_used is False
```

---

## 5. JSON 往復変換テスト

```python
class TestSerialization:
    """Pydantic モデルのシリアライズ/デシリアライズテスト。"""

    def test_character_state_roundtrip(self, initial_state: CharacterState) -> None:
        """CharacterState の JSON 往復変換。"""
        json_str = initial_state.model_dump_json()
        restored = CharacterState.model_validate_json(json_str)
        assert initial_state == restored

    def test_daily_event_roundtrip(self, sample_event: DailyEvent) -> None:
        """DailyEvent の JSON 往復変換。"""
        json_str = sample_event.model_dump_json()
        restored = DailyEvent.model_validate_json(json_str)
        assert sample_event == restored
```
