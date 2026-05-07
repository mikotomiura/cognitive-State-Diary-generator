# Pydantic 実装例集

> CSDG プロジェクトにおける Pydantic v2 モデルの実装パターン。

---

## 1. Structured Outputs 対応モデル

LLM の Structured Outputs として使用するモデルでは、`description` が LLM への指示になる。

```python
class CriticScore(BaseModel):
    """Criticによる日記の定量評価結果。"""

    temporal_consistency: int = Field(
        description="過去の日記・状態との時間的整合性 (1: 明確な矛盾 〜 5: 完璧な統合)",
    )
    emotional_plausibility: int = Field(
        description="イベントに対する感情変化の妥当性 (1: 完全に不自然 〜 5: 非常に自然)",
    )
    persona_deviation: int = Field(
        description="キャラクター設定からの逸脱度 (1: 別人 〜 5: 完璧に一致)",
    )
    reject_reason: str | None = Field(
        default=None,
        description="スコアが3未満の場合、不合格の理由を具体的に記述する。全スコア3以上の場合はnull",
    )
    revision_instruction: str | None = Field(
        default=None,
        description="不合格の場合、Actorへの具体的な修正指示を記述する。合格の場合はnull",
    )

    @field_validator("temporal_consistency", "emotional_plausibility", "persona_deviation")
    @classmethod
    def validate_score_range(cls, v: int) -> int:
        """スコアを1〜5の範囲に制限する。"""
        if not (1 <= v <= 5):
            raise ValueError(f"スコアは1〜5の範囲: {v}")
        return v
```

---

## 2. イミュータブルな値オブジェクト

変更されるべきでないモデルには `frozen=True` を設定する。

```python
class DailyEvent(BaseModel):
    """日次イベント定義。シナリオで事前定義され、変更されない。"""

    model_config = {"frozen": True}

    day: int = Field(description="経過日数 (1-7)")
    event_type: str = Field(description="positive / negative / neutral")
    domain: str = Field(description="仕事 / 人間関係 / 趣味 / 内省 / 思想")
    description: str = Field(description="起きた出来事の客観的な記述")
    emotional_impact: float = Field(description="感情的インパクト (-1.0 to 1.0)")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        allowed = {"positive", "negative", "neutral"}
        if v not in allowed:
            raise ValueError(f"event_type は {allowed} のいずれか: {v}")
        return v

    @field_validator("emotional_impact")
    @classmethod
    def validate_impact_range(cls, v: float) -> float:
        if not (-1.0 <= v <= 1.0):
            raise ValueError(f"emotional_impact は -1.0〜1.0: {v}")
        return v

    @field_validator("description")
    @classmethod
    def validate_description_length(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError(f"description は10文字以上: {len(v)}文字")
        return v
```

---

## 3. ログ用の複合モデル

```python
from datetime import datetime

class GenerationRecord(BaseModel):
    """1Dayの生成記録。"""

    day: int
    event: DailyEvent
    initial_state: CharacterState
    final_state: CharacterState
    diary_text: str
    critic_scores: list[CriticScore] = Field(
        default_factory=list,
        description="リトライ含む全てのCriticScore",
    )
    retry_count: int = Field(default=0)
    fallback_used: bool = Field(default=False)
    temperature_used: float
    phase1_duration_ms: int
    phase2_duration_ms: int
    phase3_duration_ms: int
    expected_delta: dict[str, float] = Field(default_factory=dict)
    actual_delta: dict[str, float] = Field(default_factory=dict)
    deviation: dict[str, float] = Field(default_factory=dict)


class PipelineLog(BaseModel):
    """パイプライン全体のログ。"""

    pipeline_version: str = Field(default="1.0.0")
    executed_at: datetime = Field(default_factory=datetime.now)
    config_summary: dict[str, object] = Field(default_factory=dict)
    prompt_hashes: dict[str, str] = Field(default_factory=dict)
    records: list[GenerationRecord] = Field(default_factory=list)
    total_duration_ms: int = Field(default=0)
    total_api_calls: int = Field(default=0)
    total_retries: int = Field(default=0)
    total_fallbacks: int = Field(default=0)
```

---

## 4. model_copy による状態更新

`CharacterState` は `frozen=True` ではないが、明示的にコピーして更新するパターンを推奨する。

```python
# スライディングウィンドウの更新
def update_memory(state: CharacterState, new_summary: str) -> CharacterState:
    """memory_buffer に新しいサマリを追加し、ウィンドウサイズを維持する。"""
    updated_buffer = state.memory_buffer + [new_summary]
    return state.model_copy(update={"memory_buffer": updated_buffer[-3:]})

# フォールバック時の状態コピー
def create_fallback_state(prev_state: CharacterState, day: int) -> CharacterState:
    """前日の状態をコピーし、暫定サマリを挿入する。"""
    fallback = prev_state.model_copy(deep=True)
    fallback.memory_buffer.append(f"[Day {day}: フォールバック]")
    fallback.memory_buffer = fallback.memory_buffer[-3:]
    return fallback
```

---

## 5. JSON シリアライズ・デシリアライズ

```python
# モデル → JSON文字列
json_str = state.model_dump_json(indent=2)

# JSON文字列 → モデル（バリデーション付き）
restored = CharacterState.model_validate_json(json_str)

# モデル → dict
data = state.model_dump()

# dict → モデル
restored = CharacterState.model_validate(data)

# LLM の Structured Outputs 用スキーマ取得
schema = CharacterState.model_json_schema()
```
