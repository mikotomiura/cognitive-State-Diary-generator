# Python 実装例集

> CSDG プロジェクトで推奨されるPythonの実装パターン集。

---

## 1. 型アノテーション付き関数定義

```python
from typing import TypeAlias
from csdg.schemas import CharacterState, DailyEvent, CriticScore

EmotionMap: TypeAlias = dict[str, float]

def compute_expected_delta(
    event: DailyEvent,
    sensitivity: EmotionMap,
) -> EmotionMap:
    """イベントの emotional_impact から各パラメータの期待変動幅を算出する。

    Args:
        event: 当日のイベント定義。
        sensitivity: 感情感度係数マップ。

    Returns:
        パラメータ名をキー、期待変動幅を値とするマップ。
    """
    return {
        param: event.emotional_impact * coeff
        for param, coeff in sensitivity.items()
    }
```

---

## 2. Google style docstring の完全な例

```python
class PipelineRunner:
    """3フェーズパイプラインの実行を制御するクラス。

    Day 1〜Day 7 のループ、リトライ制御、Self-Healing フォールバック、
    memory_buffer のスライディングウィンドウ管理を担当する。

    Attributes:
        config: パイプライン設定。
        actor: Actor インスタンス。
        critic: Critic インスタンス。

    Example:
        >>> runner = PipelineRunner(config, actor, critic)
        >>> log = await runner.run(scenario, initial_state)
        >>> print(f"成功: {log.total_days_succeeded}/7")
    """

    def __init__(
        self,
        config: CSDGConfig,
        actor: Actor,
        critic: Critic,
    ) -> None:
        """PipelineRunner を初期化する。

        Args:
            config: パイプライン設定（リトライ上限、Temperature等）。
            actor: Phase 1/2 の生成を担当する Actor。
            critic: Phase 3 の評価を担当する Critic。
        """
        self.config = config
        self.actor = actor
        self.critic = critic
```

---

## 3. エラーハンドリングとフォールバック

```python
import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)

async def run_phase1_with_fallback(
    self,
    prev_state: CharacterState,
    event: DailyEvent,
    day: int,
) -> CharacterState:
    """Phase 1 を実行し、失敗時はフォールバックする。

    Args:
        prev_state: 前日の状態。
        event: 当日のイベント。
        day: 処理中のDay番号。

    Returns:
        更新された状態。フォールバック時は前日の状態のコピー。
    """
    for attempt in range(self.config.max_retries):
        try:
            new_state = await self.actor.update_state(prev_state, event)
            logger.info("[Day %d] Phase 1: OK (attempt %d)", day, attempt + 1)
            return new_state
        except ValidationError as e:
            logger.warning(
                "[Day %d] Phase 1: ValidationError (attempt %d/%d): %d errors",
                day, attempt + 1, self.config.max_retries, e.error_count(),
            )

    # フォールバック: 前日の状態をコピー
    logger.warning("[Day %d] Phase 1: フォールバック発動 — 前日状態をコピー", day)
    fallback_state = prev_state.model_copy(deep=True)
    summary = f"[Day {day}: フォールバック - 状態更新に失敗]"
    fallback_state.memory_buffer.append(summary)
    fallback_state.memory_buffer = fallback_state.memory_buffer[-3:]
    return fallback_state
```

---

## 4. 非同期処理のパターン

```python
import asyncio
from csdg.engine.llm_client import LLMClient

class Actor:
    """Phase 1/2 の生成を担当する Actor。"""

    def __init__(self, client: LLMClient, config: CSDGConfig) -> None:
        self._client = client
        self._config = config

    async def update_state(
        self,
        prev_state: CharacterState,
        event: DailyEvent,
    ) -> CharacterState:
        """Phase 1: 状態遷移。"""
        system_prompt = self._load_prompt("prompts/System_Persona.md")
        user_prompt = self._build_state_update_prompt(prev_state, event)

        return await self._client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=CharacterState,
            temperature=self._config.initial_temperature,
        )

    def _load_prompt(self, path: str) -> str:
        """プロンプトファイルを読み込む。"""
        return Path(path).read_text(encoding="utf-8")

    def _build_state_update_prompt(
        self,
        prev_state: CharacterState,
        event: DailyEvent,
    ) -> str:
        """Phase 1 用プロンプトを構築する。"""
        template = self._load_prompt("prompts/Prompt_StateUpdate.md")
        return template.format(
            previous_state=prev_state.model_dump_json(indent=2),
            event=event.model_dump_json(indent=2),
            memory_buffer="\n".join(prev_state.memory_buffer) or "(記憶なし)",
        )
```

---

## 5. 設定値の取得パターン

```python
from csdg.config import CSDGConfig

# ✅ 正しい: config から取得
config = CSDGConfig()
temperatures = config.temperature_schedule
sensitivity = config.emotion_sensitivity

# ✅ 正しい: 関数の引数として受け取る（テスタビリティ向上）
def create_pipeline(config: CSDGConfig) -> PipelineRunner:
    client = OpenAIClient(api_key=config.llm_api_key, model=config.llm_model)
    actor = Actor(client, config)
    critic = Critic(client, config)
    return PipelineRunner(config, actor, critic)
```

---

## 6. ログレベルの使い分け

```python
# DEBUG: 開発時の詳細情報
logger.debug("プロンプトトークン数: %d", token_count)
logger.debug("LLMレスポンス先頭: %s", response[:100])

# INFO: 正常な処理の進行状況
logger.info("[Day %d] Phase 2: Content Generation ... OK (%.1fs)", day, elapsed)
logger.info("[CSDG] Pipeline complete (%d/%d days)", succeeded, total)

# WARNING: 回復可能な問題
logger.warning("[Day %d] Phase 3: Reject (score: %d/%d/%d) → Retry %d/%d",
               day, s1, s2, s3, retry, max_retries)
logger.warning("[Day %d] Phase 1: フォールバック発動", day)

# ERROR: 回復不能な問題
logger.error("[Day %d] スキップ: %s", day, str(exc))

# CRITICAL: システム停止
logger.critical("パイプライン中断: 連続 %d Day 失敗", consecutive_failures)
```
