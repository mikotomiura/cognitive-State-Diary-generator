# Pydantic バリデーションレシピ集

> CSDG プロジェクトでよく使うバリデーションパターンのレシピ。

---

## 1. 数値範囲のクランプ（値を修正して受け入れる）

```python
@field_validator("fatigue", "motivation", "stress")
@classmethod
def clamp_continuous(cls, v: float) -> float:
    """範囲外の値を境界値にクランプする。エラーにはしない。"""
    return max(-1.0, min(1.0, v))
```

**使用場面:** LLM が -1.0〜1.0 の範囲外の値を生成した場合に、エラーにせずに正規化する。

---

## 2. 数値範囲の厳密チェック（範囲外はエラー）

```python
@field_validator("temporal_consistency", "emotional_plausibility", "persona_deviation")
@classmethod
def validate_score_range(cls, v: int) -> int:
    """スコアが1〜5の範囲外の場合は ValidationError を発生させる。"""
    if not (1 <= v <= 5):
        raise ValueError(f"スコアは1〜5の範囲: {v}")
    return v
```

**使用場面:** CriticScore のスコアなど、範囲外の値が論理的に無効な場合。

---

## 3. リストのサイズ制限

```python
@field_validator("memory_buffer")
@classmethod
def limit_buffer(cls, v: list[str]) -> list[str]:
    """末尾の要素を残してサイズを制限する（FIFO）。"""
    return v[-3:] if len(v) > 3 else v
```

**使用場面:** スライディングウィンドウのサイズ制限。

---

## 4. 列挙値のチェック

```python
@field_validator("event_type")
@classmethod
def validate_event_type(cls, v: str) -> str:
    """許可された値のみを受け入れる。"""
    allowed = {"positive", "negative", "neutral"}
    if v not in allowed:
        raise ValueError(f"event_type は {allowed} のいずれか: {v}")
    return v
```

**使用場面:** `event_type` や `domain` など、取りうる値が限定されるフィールド。
**代替案:** `Literal["positive", "negative", "neutral"]` 型を使う方法もあるが、エラーメッセージのカスタマイズができない。

---

## 5. 文字列の最小長チェック

```python
@field_validator("description")
@classmethod
def validate_min_length(cls, v: str) -> str:
    """空文字列や短すぎる文字列を拒否する。"""
    if len(v) < 10:
        raise ValueError(f"description は10文字以上必要: {len(v)}文字")
    return v
```

---

## 6. 辞書のキー制限

```python
KNOWN_CHARACTERS: set[str] = {"深森那由他", "ミナ"}

@field_validator("relationships")
@classmethod
def validate_known_characters(cls, v: dict[str, float]) -> dict[str, float]:
    """未知のキャラクターが含まれていないか確認する。"""
    unknown = set(v.keys()) - KNOWN_CHARACTERS
    if unknown:
        raise ValueError(f"未知のキャラクター: {unknown}")
    return v
```

**使用場面:** `relationships` に定義外の人物が追加されることを防ぐ。

---

## 7. フィールド間の依存バリデーション（model_validator）

```python
from pydantic import model_validator

class CriticScore(BaseModel):
    temporal_consistency: int
    emotional_plausibility: int
    persona_deviation: int
    reject_reason: str | None = None
    revision_instruction: str | None = None

    @model_validator(mode="after")
    def check_reject_fields(self) -> "CriticScore":
        """Reject時はreject_reasonとrevision_instructionが必須。"""
        is_reject = any(
            getattr(self, f) < 3
            for f in ["temporal_consistency", "emotional_plausibility", "persona_deviation"]
        )
        if is_reject and not self.reject_reason:
            raise ValueError("Reject時はreject_reasonが必須")
        if is_reject and not self.revision_instruction:
            raise ValueError("Reject時はrevision_instructionが必須")
        return self
```

**使用場面:** 複数フィールドの整合性を検証する場合。

---

## 8. テストでのバリデーション確認パターン

```python
import pytest
from pydantic import ValidationError

def test_clamp_upper_bound() -> None:
    """1.0を超える値はクランプされる（エラーにならない）。"""
    state = CharacterState(fatigue=1.5, motivation=0, stress=0,
                           current_focus="test", growth_theme="test")
    assert state.fatigue == 1.0

def test_invalid_event_type() -> None:
    """不正な event_type で ValidationError が発生する。"""
    with pytest.raises(ValidationError, match="event_type"):
        DailyEvent(day=1, event_type="invalid", domain="仕事",
                   description="テスト用のイベント記述です", emotional_impact=0.5)

def test_roundtrip_serialization() -> None:
    """JSON往復変換で値が保持される。"""
    original = CharacterState(fatigue=0.5, motivation=-0.3, stress=0.1,
                              current_focus="テスト", growth_theme="テスト")
    restored = CharacterState.model_validate_json(original.model_dump_json())
    assert original == restored
```
