# フィクスチャパターン集

> CSDG プロジェクトで使用するpytestフィクスチャの設計パターン。

---

## 1. conftest.py の構成

```python
"""tests/conftest.py — 共通フィクスチャ定義。"""

import pytest
from unittest.mock import AsyncMock

from csdg.config import CSDGConfig
from csdg.schemas import CharacterState, DailyEvent, CriticScore
from csdg.engine.llm_client import LLMClient


# ─── データフィクスチャ ───


@pytest.fixture
def initial_state() -> CharacterState:
    """シナリオの初期状態 h_0。"""
    return CharacterState(
        fatigue=0.1,
        motivation=0.2,
        stress=-0.1,
        current_focus="来週の社内コードレビュー会の準備",
        unresolved_issue=None,
        growth_theme="「考えること」と「生きること」の折り合い",
        memory_buffer=[],
        relationships={"深森那由他": 0.6, "ミナ": 0.4},
    )


@pytest.fixture
def sample_event() -> DailyEvent:
    """Day 1 のイベント（neutral, impact=+0.2）。"""
    return DailyEvent(
        day=1,
        event_type="neutral",
        domain="仕事",
        description="社内ツールの自動化スクリプトが完成し、30分かかっていた作業が2分に短縮された",
        emotional_impact=0.2,
    )


@pytest.fixture
def high_impact_event() -> DailyEvent:
    """Day 4 のイベント（negative, impact=-0.9）。ストレステスト用。"""
    return DailyEvent(
        day=4,
        event_type="negative",
        domain="仕事",
        description="全社会議で経営陣が全業務のAI自動化ロードマップを発表した",
        emotional_impact=-0.9,
    )


@pytest.fixture
def pass_score() -> CriticScore:
    """全スコア3以上の合格スコア。"""
    return CriticScore(
        temporal_consistency=4,
        emotional_plausibility=4,
        persona_deviation=5,
    )


@pytest.fixture
def reject_score() -> CriticScore:
    """persona_deviation が2の不合格スコア。"""
    return CriticScore(
        temporal_consistency=4,
        emotional_plausibility=3,
        persona_deviation=2,
        reject_reason="絵文字が使用されている",
        revision_instruction="絵文字を削除し、言葉のみで感情を表現してください",
    )


@pytest.fixture
def sample_diary() -> str:
    """テスト用の日記テキスト。"""
    return (
        "今日、自動化スクリプトが完成した。30分の作業が2分になった。\n\n"
        "チームからは感謝された。でも、わたしの中では妙な手持ち無沙汰が残っている。\n"
        "効率化が成功したのに、この空虚さは何なんだろう......。\n\n"
        "帰り道、ふと利休のことを考えた。"
        "あの人は、お茶を点てるのに最も効率的な方法を選ばなかった。\n"
        "むしろ非効率な所作にこそ意味があると信じていた......のかもしれない。"
    )


# ─── 設定フィクスチャ ───


@pytest.fixture
def test_config() -> CSDGConfig:
    """テスト用の設定（APIキーはダミー）。"""
    return CSDGConfig(
        llm_api_key="test-api-key-dummy",
        llm_model="gpt-4o",
        max_retries=3,
        initial_temperature=0.7,
        output_dir="test_output",
    )


@pytest.fixture
def emotion_sensitivity() -> dict[str, float]:
    """テスト用の感情感度係数。"""
    return {
        "stress": -0.3,
        "motivation": 0.4,
        "fatigue": -0.2,
    }


# ─── モックフィクスチャ ───


@pytest.fixture
def mock_llm_client() -> LLMClient:
    """LLM API をモックしたクライアント。"""
    return AsyncMock(spec=LLMClient)


@pytest.fixture
def mock_llm_pass(mock_llm_client: LLMClient, initial_state: CharacterState, pass_score: CriticScore) -> LLMClient:
    """全Phaseが1回で成功するモック。"""
    mock_llm_client.generate_structured.side_effect = [initial_state, pass_score]
    mock_llm_client.generate_text.return_value = "テスト用日記テキスト"
    return mock_llm_client


@pytest.fixture
def mock_llm_retry(mock_llm_client: LLMClient, initial_state: CharacterState, reject_score: CriticScore, pass_score: CriticScore) -> LLMClient:
    """Phase 3で1回Reject → リトライでPassするモック。"""
    mock_llm_client.generate_structured.side_effect = [initial_state, reject_score, pass_score]
    mock_llm_client.generate_text.return_value = "テスト用日記テキスト"
    return mock_llm_client
```

---

## 2. フィクスチャの使い方

```python
class TestPipelineNormalFlow:
    """パイプラインの正常系テスト。"""

    @pytest.mark.asyncio
    async def test_single_day_pass(
        self,
        test_config: CSDGConfig,
        mock_llm_pass: LLMClient,
        sample_event: DailyEvent,
        initial_state: CharacterState,
    ) -> None:
        """1Day が1回で Pass する場合。"""
        actor = Actor(mock_llm_pass, test_config)
        critic = Critic(mock_llm_pass, test_config)
        pipeline = PipelineRunner(test_config, actor, critic)

        record = await pipeline.run_single_day(sample_event, initial_state, day=1)

        assert record.retry_count == 0
        assert record.fallback_used is False
```

---

## 3. フィクスチャ設計の原則

| 原則 | 説明 |
|---|---|
| **最小構成** | フィクスチャは必要最小限のデータのみを含める |
| **独立性** | フィクスチャ間に順序依存を作らない |
| **命名の明確さ** | `initial_state`, `pass_score`, `high_impact_event` のように用途が分かる名前 |
| **スコープ** | データフィクスチャは `function`（デフォルト）、設定は `session` でもよい |
| **再利用** | 共通のフィクスチャは `conftest.py` に集約。テストファイル固有のものはローカル定義 |

---

## 4. パラメタライズとフィクスチャの組み合わせ

```python
@pytest.mark.parametrize("impact,expected_stress_direction", [
    (0.6, "decrease"),    # positive → stress 低下
    (-0.5, "increase"),   # negative → stress 上昇
    (0.0, "unchanged"),   # neutral → stress 変化なし
])
def test_stress_direction(
    self,
    impact: float,
    expected_stress_direction: str,
    emotion_sensitivity: dict[str, float],
) -> None:
    """emotional_impact の符号に応じて stress の変動方向が正しい。"""
    event = DailyEvent(
        day=1, event_type="neutral", domain="仕事",
        description="テスト用のイベント記述です",
        emotional_impact=impact,
    )
    delta = compute_expected_delta(event, emotion_sensitivity)

    if expected_stress_direction == "decrease":
        assert delta["stress"] < 0
    elif expected_stress_direction == "increase":
        assert delta["stress"] > 0
    else:
        assert delta["stress"] == 0.0
```
