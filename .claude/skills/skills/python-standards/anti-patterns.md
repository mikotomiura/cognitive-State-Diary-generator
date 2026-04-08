# Python アンチパターン集

> CSDG プロジェクトで避けるべきコーディングパターンと、正しい代替案。

---

## 1. 型アノテーションの省略

```python
# ❌ アンチパターン: 型なし
def clamp(value):
    return max(-1.0, min(1.0, value))

# ✅ 正しい: 型アノテーション付き
def clamp(value: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
    """値を許容範囲にクランプする。"""
    return max(min_val, min(max_val, value))
```

---

## 2. Any 型の濫用

```python
# ❌ アンチパターン: Any で逃げる
from typing import Any
def parse_response(response: Any) -> Any:
    return response["choices"][0]["message"]["content"]

# ✅ 正しい: 具体的な型を定義
from pydantic import BaseModel
class LLMResponse(BaseModel):
    content: str
    finish_reason: str

async def parse_response(raw: dict[str, object]) -> LLMResponse:
    """LLMのレスポンスをパースする。"""
    ...
```

---

## 3. 裸の except

```python
# ❌ アンチパターン: 何をキャッチしているか不明
try:
    state = CharacterState.model_validate_json(raw)
except:
    state = previous_state

# ❌ アンチパターン: 握りつぶし
try:
    state = CharacterState.model_validate_json(raw)
except Exception:
    pass

# ✅ 正しい: 具体的な例外 + ロギング + 適切な処理
try:
    state = CharacterState.model_validate_json(raw)
except ValidationError as e:
    logger.warning("バリデーションエラー: %d errors", e.error_count())
    raise  # 呼び出し元でリトライ制御
```

---

## 4. print() によるデバッグ

```python
# ❌ アンチパターン: print デバッグ
print(f"state: {state}")
print(f"score: {score}")

# ✅ 正しい: logging モジュール
logger.debug("state: %s", state.model_dump_json())
logger.info("score: %d/%d/%d", s1, s2, s3)
```

---

## 5. マジックナンバー

```python
# ❌ アンチパターン: 何の数値か分からない
if score.temporal_consistency >= 3 and score.emotional_plausibility >= 3:
    return True
temperature = 0.7 - (attempt * 0.2)

# ✅ 正しい: 設定値として管理
PASS_THRESHOLD = 3  # CriticScore の合格ライン（schemas.py で定義）

def judge(score: CriticScore) -> bool:
    return all(
        getattr(score, f) >= PASS_THRESHOLD
        for f in ["temporal_consistency", "emotional_plausibility", "persona_deviation"]
    )

# Temperature は config から取得
temperature = config.temperature_schedule[attempt]
```

---

## 6. プロンプトのハードコード

```python
# ❌ アンチパターン: プロンプトをコードに埋め込み
system_prompt = """あなたは26歳のバックエンドエンジニア、三浦とこみです。
哲学的な思考が特徴で、絵文字は使いません..."""

# ✅ 正しい: 外部ファイルから読み込み
system_prompt = Path("prompts/System_Persona.md").read_text(encoding="utf-8")
```

---

## 7. ミュータブルデフォルト引数

```python
# ❌ アンチパターン: ミュータブルデフォルト
def create_state(memory_buffer: list[str] = []) -> CharacterState:
    ...  # すべての呼び出しで同じリストオブジェクトを共有してしまう

# ✅ 正しい: None パターンまたは default_factory
def create_state(memory_buffer: list[str] | None = None) -> CharacterState:
    buffer = memory_buffer if memory_buffer is not None else []
    ...

# ✅ Pydantic の場合: default_factory
class CharacterState(BaseModel):
    memory_buffer: list[str] = Field(default_factory=list)
```

---

## 8. 循環参照

```python
# ❌ アンチパターン: schemas.py が actor.py を import
# schemas.py
from csdg.engine.actor import Actor  # 循環参照！

# ✅ 正しい: 依存は一方向 (actor.py → schemas.py)
# actor.py
from csdg.schemas import CharacterState, DailyEvent
```

---

## 9. 同期的な API 呼び出し

```python
# ❌ アンチパターン: 同期呼び出し（将来の並列化を阻害）
def generate_diary(self, state: CharacterState) -> str:
    response = self.client.chat.completions.create(...)
    return response.choices[0].message.content

# ✅ 正しい: async/await
async def generate_diary(self, state: CharacterState) -> str:
    response = await self.client.chat.completions.create(...)
    return response.choices[0].message.content
```

---

## 10. 深いネストと長い関数

```python
# ❌ アンチパターン: 深いネスト
def process_day(day, event, state):
    if event is not None:
        if event.event_type in ["positive", "negative", "neutral"]:
            if state is not None:
                try:
                    new_state = update(state, event)
                    if new_state.fatigue <= 1.0:
                        ...  # 5段階のネスト

# ✅ 正しい: 早期リターンでフラット化
def process_day(
    day: int,
    event: DailyEvent,
    state: CharacterState,
) -> CharacterState:
    """1日分のパイプラインを処理する。"""
    if event is None:
        raise ValueError("event は必須")
    if state is None:
        raise ValueError("state は必須")

    new_state = update(state, event)
    return new_state
```
