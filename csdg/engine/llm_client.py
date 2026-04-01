"""
LLM API 呼び出しの抽象インターフェースと各プロバイダー実装。

architecture.md §8.3 に基づき、LLM 呼び出しを抽象化する。
AnthropicClient は tool_use パターン、GeminiClient は response_schema パターンで
構造化出力を実現する。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

from anthropic import AsyncAnthropic
from anthropic.types import TextBlock, ToolUseBlock
from pydantic import BaseModel

if TYPE_CHECKING:
    from anthropic.types.tool_param import ToolParam

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient(ABC):
    """LLM API 呼び出しの抽象インターフェース。

    Phase 1, 3 で使用する構造化生成 (Structured Outputs) と、
    Phase 2 で使用するプレーンテキスト生成の2つのメソッドを定義する。
    """

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float,
    ) -> T:
        """Structured Outputs による構造化生成。

        Args:
            system_prompt: System Prompt テキスト (System_Persona.md)。
            user_prompt: User Prompt テキスト (Phase 固有プロンプト + 動的データ)。
            response_model: 出力の Pydantic モデルクラス。
            temperature: 生成時の Temperature パラメータ。

        Returns:
            response_model のインスタンス。

        Raises:
            pydantic.ValidationError: LLM 出力がスキーマに適合しない場合。
            anthropic.APIError: API 呼び出しに失敗した場合。
        """
        ...

    @abstractmethod
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int = 4096,
    ) -> str:
        """プレーンテキスト生成。

        Args:
            system_prompt: System Prompt テキスト (System_Persona.md)。
            user_prompt: User Prompt テキスト (Prompt_Generator.md + 動的データ)。
            temperature: 生成時の Temperature パラメータ。
            max_tokens: 最大トークン数。

        Returns:
            生成されたテキスト。

        Raises:
            ValueError: 生成結果が空文字列の場合。
            anthropic.APIError: API 呼び出しに失敗した場合。
        """
        ...


class AnthropicClient(LLMClient):
    """Anthropic Claude API を使用した LLMClient 実装。

    AsyncAnthropic クライアントを内部で保持し、
    tool_use パターンによる構造化生成とプレーンテキスト生成を提供する。
    """

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        """AnthropicClient を初期化する。

        Args:
            api_key: Anthropic API キー。
            model: 使用する LLM モデル名 (例: "claude-sonnet-4-20250514")。
            base_url: API のベース URL。
        """
        self._client = AsyncAnthropic(api_key=api_key, base_url=base_url, max_retries=5)
        self._model = model
        logger.debug("AnthropicClient initialized: model=%s, base_url=%s", model, base_url)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float,
    ) -> T:
        """tool_use パターンによる構造化生成。

        response_model の JSON Schema を tools パラメータに渡し、
        tool_choice で強制呼び出しすることで構造化出力を取得する。

        Args:
            system_prompt: System Prompt テキスト。
            user_prompt: User Prompt テキスト。
            response_model: 出力の Pydantic モデルクラス。
            temperature: 生成時の Temperature パラメータ。

        Returns:
            response_model のインスタンス。

        Raises:
            pydantic.ValidationError: LLM 出力がスキーマに適合しない場合。
            ValueError: tool_use ブロックが見つからない場合。
            anthropic.APIError: API 呼び出しに失敗した場合。
        """
        logger.debug(
            "generate_structured: model=%s, response_model=%s, temperature=%.2f",
            self._model,
            response_model.__name__,
            temperature,
        )

        tool_def: ToolParam = {
            "name": "structured_output",
            "description": "構造化データを出力するためのツール",
            "input_schema": response_model.model_json_schema(),
        }

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[tool_def],
            tool_choice={"type": "tool", "name": "structured_output"},
            temperature=temperature,
        )

        logger.debug(
            "generate_structured response: input_tokens=%d, output_tokens=%d",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        # tool_use ブロックを探す
        for block in response.content:
            if isinstance(block, ToolUseBlock):
                return response_model.model_validate(block.input)

        raise ValueError(
            f"tool_use ブロックが見つかりません (response content types: {[b.type for b in response.content]})"
        )

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int = 4096,
    ) -> str:
        """プレーンテキスト生成。

        Anthropic API の system パラメータに system_prompt を渡し、
        messages に user_prompt を渡して自由テキストを生成する。

        Args:
            system_prompt: System Prompt テキスト。
            user_prompt: User Prompt テキスト。
            temperature: 生成時の Temperature パラメータ。
            max_tokens: 最大トークン数。

        Returns:
            生成されたテキスト。

        Raises:
            ValueError: 生成結果が空文字列の場合。
            anthropic.APIError: API 呼び出しに失敗した場合。
        """
        logger.debug(
            "generate_text: model=%s, temperature=%.2f, max_tokens=%d",
            self._model,
            temperature,
            max_tokens,
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
        )

        logger.debug(
            "generate_text response: input_tokens=%d, output_tokens=%d",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        first_block = response.content[0] if response.content else None
        content = first_block.text if isinstance(first_block, TextBlock) else ""
        if not content:
            raise ValueError("LLM がテキストを返しませんでした (空文字列)")

        return content


def _strip_additional_properties(schema: dict[str, Any]) -> dict[str, Any]:
    """Pydantic の JSON Schema から additionalProperties を再帰的に除去する。

    Gemini API は additionalProperties をサポートしないため、
    Pydantic が生成するスキーマから除去する必要がある。
    """
    schema.pop("additionalProperties", None)
    if "properties" in schema and isinstance(schema["properties"], dict):
        for prop_schema in schema["properties"].values():
            if isinstance(prop_schema, dict):
                _strip_additional_properties(prop_schema)
    if "$defs" in schema and isinstance(schema["$defs"], dict):
        for def_schema in schema["$defs"].values():
            if isinstance(def_schema, dict):
                _strip_additional_properties(def_schema)
    # anyOf / allOf / oneOf 内のスキーマも処理
    for key in ("anyOf", "allOf", "oneOf"):
        if key in schema and isinstance(schema[key], list):
            for item in schema[key]:
                if isinstance(item, dict):
                    _strip_additional_properties(item)
    if "items" in schema and isinstance(schema["items"], dict):
        _strip_additional_properties(schema["items"])
    return schema


# Gemini のフォールバックモデルリスト (利用可能性が変動するため順番に試す)
_GEMINI_FALLBACK_MODELS: tuple[str, ...] = (
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
)

# 429 レート制限時のリトライ設定
_GEMINI_RATE_LIMIT_MAX_RETRIES = 2
_GEMINI_RATE_LIMIT_DEFAULT_DELAY = 20.0


class GeminiClient(LLMClient):
    """Google Gemini API を使用した LLMClient 実装。

    google-genai SDK の AsyncClient (client.aio) を内部で保持し、
    response_schema パターンによる構造化生成とプレーンテキスト生成を提供する。
    開発・デバッグ用途を想定。

    エラーハンドリング:
    - 429 (RESOURCE_EXHAUSTED): retryDelay 秒待って同一モデルで再試行 (最大2回)
    - 404 (NOT_FOUND): 廃止モデルとして記録し、即座に次のモデルへ
    - その他: 次のフォールバックモデルへローテーション
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_models: tuple[str, ...] | None = None,
    ) -> None:
        """GeminiClient を初期化する。

        Args:
            api_key: Google AI Studio の API キー。
            model: 優先使用する LLM モデル名 (例: "gemini-2.0-flash")。
            fallback_models: フォールバックモデルのリスト。
                None の場合はデフォルトリストを使用。
        """
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._primary_model = model
        self._model = model
        self._dead_models: set[str] = set()

        if fallback_models is None:
            fallback_models = _GEMINI_FALLBACK_MODELS
        seen: set[str] = {model}
        self._model_rotation: list[str] = [model]
        for m in fallback_models:
            if m not in seen:
                self._model_rotation.append(m)
                seen.add(m)

        logger.info(
            "GeminiClient initialized: primary=%s, rotation=%s",
            model,
            self._model_rotation,
        )

    @staticmethod
    def _extract_retry_delay(error: Exception) -> float | None:
        """429 エラーから retryDelay 秒数を抽出する。"""
        import re as _re

        msg = str(error)
        if "429" not in msg and "RESOURCE_EXHAUSTED" not in msg:
            return None
        match = _re.search(r"retryDelay.*?(\d+(?:\.\d+)?)\s*s", msg)
        return float(match.group(1)) if match else _GEMINI_RATE_LIMIT_DEFAULT_DELAY

    @staticmethod
    def _is_not_found(error: Exception) -> bool:
        """404 NOT_FOUND エラーかどうかを判定する。"""
        msg = str(error)
        return "404" in msg and "NOT_FOUND" in msg

    def _alive_models(self) -> list[str]:
        """404 で廃止されたモデルを除外した利用可能モデルリスト。"""
        return [m for m in self._model_rotation if m not in self._dead_models]

    def _reset_model(self) -> None:
        """モデルをプライマリ (廃止済みなら最初の生存モデル) にリセットする。"""
        alive = self._alive_models()
        if not alive:
            return
        target = self._primary_model if self._primary_model in alive else alive[0]
        if self._model != target:
            logger.info("Gemini model reset: %s -> %s", self._model, target)
            self._model = target

    async def _call_with_fallback(self, call_fn: Any) -> Any:
        """フォールバック + 429 リトライの共通ロジック。

        Args:
            call_fn: モデル名を受け取り結果を返す async callable。

        Returns:
            call_fn の戻り値。
        """
        import asyncio as _asyncio

        alive = self._alive_models()
        if not alive:
            raise ValueError("利用可能な Gemini モデルがありません (全て 404)")

        last_error: Exception | None = None
        for model in alive:
            self._model = model
            rate_retries = 0
            while True:
                try:
                    result = await call_fn(model)
                    self._reset_model()
                    return result
                except Exception as e:
                    if self._is_not_found(e):
                        logger.warning("Gemini %s -> 404 (deprecated), skipping", model)
                        self._dead_models.add(model)
                        last_error = e
                        break

                    delay = self._extract_retry_delay(e)
                    if delay is not None and rate_retries < _GEMINI_RATE_LIMIT_MAX_RETRIES:
                        rate_retries += 1
                        logger.warning(
                            "Gemini %s -> 429, waiting %.0fs (%d/%d)",
                            model,
                            delay,
                            rate_retries,
                            _GEMINI_RATE_LIMIT_MAX_RETRIES,
                        )
                        await _asyncio.sleep(delay)
                        continue

                    logger.warning("Gemini %s failed: %s", model, e)
                    last_error = e
                    break

        self._reset_model()
        raise last_error or ValueError("全 Gemini モデルで失敗")

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float,
    ) -> T:
        """response_schema パターンによる構造化生成 (フォールバック + 429 リトライ付き)。"""
        from google.genai import types as genai_types

        clean_schema = _strip_additional_properties(response_model.model_json_schema().copy())

        async def _call(model: str) -> T:
            logger.debug(
                "generate_structured: model=%s, schema=%s, temp=%.2f",
                model,
                response_model.__name__,
                temperature,
            )
            resp = await self._client.aio.models.generate_content(
                model=model,
                contents=user_prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=clean_schema,
                ),
            )
            text = resp.text or ""
            if not text:
                raise ValueError("Gemini が構造化データを返しませんでした")
            logger.debug("generate_structured: %d chars (model=%s)", len(text), model)
            return response_model.model_validate_json(text)

        return await self._call_with_fallback(_call)  # type: ignore[no-any-return]

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int = 4096,
    ) -> str:
        """プレーンテキスト生成 (フォールバック + 429 リトライ付き)。"""
        from google.genai import types as genai_types

        async def _call(model: str) -> str:
            logger.debug(
                "generate_text: model=%s, temp=%.2f, max_tokens=%d",
                model,
                temperature,
                max_tokens,
            )
            resp = await self._client.aio.models.generate_content(
                model=model,
                contents=user_prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            content = resp.text or ""
            if not content:
                raise ValueError("LLM がテキストを返しませんでした")
            logger.debug("generate_text: %d chars (model=%s)", len(content), model)
            return content

        return await self._call_with_fallback(_call)  # type: ignore[no-any-return]
