"""LLM レスポンスキャッシュ層 (F-09)。

`LLMClient` の Decorator として透過的にキャッシュを差し込み、
プロンプトチューニングサイクルでの API 呼び出しを省略する。

architecture: design.md (v3 = v1 Claude + v2 Codex マージ案 + cross-review 反映版) に準拠。
- ストレージ: sqlite3 (stdlib) + WAL モード + DB ファイル権限 0600
- キャッシュキー: SHA-256 of canonical JSON (cache_format_version / provider / model /
  kind / system_prompt / user_prompt / temperature[repr] / max_tokens / response_schema)
- 保存形式: TEXT JSON `{"kind": "structured"|"text", "payload": ...}`
- HIT 復元失敗時 (DB 破損 / スキーマ移行漏れ等) は該当 row を evict し inner を再呼び出し
  (Self-Healing 原則)

stampede 対策 (同一 key の miss が並列発生する二重呼び出し) は V1 では未実装。
CSDG は逐次パイプラインのため発生確率が低い。Best-of-N 並列化が将来戻ってきた時の
TODO として asyncio.Lock の追加を検討する。

Gemini fallback model 対応も V1 では未実装。``GeminiClient`` が内部で別モデルに
フォールバックしても primary model のキーで保存される問題があるため、
``main.py`` 側で fallback 有効時はキャッシュを無効化する運用とする。
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from typing import TYPE_CHECKING, Any, Literal, TypeVar

import pydantic

if TYPE_CHECKING:
    from pathlib import Path

    from pydantic import BaseModel

from csdg.engine.llm_client import LLMClient

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseModel")

_CACHE_FORMAT_VERSION = "1"
_DEFAULT_CACHE_DIR = "~/.cache/csdg/llm"
_CACHE_DB_FILENAME = "cache.sqlite"
_DB_FILE_MODE = 0o600  # owner read/write のみ (M-02 反映)


class ResponseCache:
    """SQLite-backed KV cache for LLM responses.

    短命接続パターン (操作ごとに ``sqlite3.connect``) でスレッド安全性を確保する。
    WAL モードで concurrent reader を許容。
    """

    def __init__(self, db_path: Path) -> None:
        """ResponseCache を初期化し、必要なら DB ファイル/テーブルを作成する。

        親ディレクトリは ``parents=True, exist_ok=True`` で自動作成する。
        DB ファイル本体は owner のみ read/write 可能 (mode 0600) に設定し、
        共有環境での平文保存リスクを最小化する。

        Args:
            db_path: sqlite ファイルのパス。
        """
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        # 既存ファイルでも所有者限定権限に揃える (M-02 反映)
        try:
            self._db_path.chmod(_DB_FILE_MODE)
        except OSError:
            # Windows などで chmod が機能しない環境では握り潰す
            logger.debug("[cache] chmod 0600 skipped (filesystem may not support)")

    def _init_schema(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_cache (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    def get(self, key: str) -> str | None:
        """キャッシュから値を取得する。

        Args:
            key: ``make_key`` で生成された SHA-256 hex キー。

        Returns:
            JSON 文字列 (``{"kind": ..., "payload": ...}``)。未登録なら None。
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "SELECT value_json FROM llm_cache WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        value: str = row[0]
        return value

    def put(self, key: str, value_json: str) -> None:
        """キャッシュに値を保存する (既存キーは上書き)。

        Args:
            key: ``make_key`` で生成された SHA-256 hex キー。
            value_json: 保存する JSON 文字列 (``{"kind": ..., "payload": ...}``)。
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO llm_cache (key, value_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    created_at = excluded.created_at
                """,
                (key, value_json, time.time()),
            )

    def delete(self, key: str) -> None:
        """指定キーを削除する (HIT 復元失敗時の eviction 用)。

        Args:
            key: 削除対象の SHA-256 hex キー。
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM llm_cache WHERE key = ?", (key,))

    @staticmethod
    def make_key(
        *,
        provider: str,
        model: str,
        kind: Literal["structured", "text"],
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int | None,
        response_schema: dict[str, Any] | None,
    ) -> str:
        """キャッシュキーを正規化 SHA-256 で生成する。

        cache_format_version をキーに含めることで将来のスキーマ変更で旧キャッシュを
        全自動失効できる。temperature は ``repr()`` 経由で文字列化し、float 表現揺れを排除。
        ``response_schema`` は Pydantic JSON Schema 全体を含めることで field 変更を検出。

        Args:
            provider: "anthropic" または "gemini"。
            model: モデル名。
            kind: "structured" または "text"。
            system_prompt: System Prompt 原文。
            user_prompt: User Prompt 原文。
            temperature: 生成時の Temperature。
            max_tokens: 最大トークン数 (text のみ。structured は None)。
            response_schema: Pydantic JSON Schema (structured のみ)。
                JSON Schema は再帰的なネスト構造を持つため value 型に Any を許容する
                (Pydantic v2 の ``model_json_schema()`` の戻り値仕様)。

        Returns:
            64 文字の SHA-256 hex 文字列。
        """
        # JSON Schema は str / int / bool / list / dict が再帰的に混在する構造を持つため
        # dict[str, Any] を使用する (規約 §2.2 で許容される LLM スキーマの妥当な使用例)
        payload: dict[str, Any] = {
            "cache_format_version": _CACHE_FORMAT_VERSION,
            "provider": provider,
            "model": model,
            "kind": kind,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "temperature": repr(temperature),
            "max_tokens": max_tokens,
            "response_schema": response_schema,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CachingLLMClient(LLMClient):
    """LLMClient の Decorator。透過的にキャッシュ層を差し込む。

    - HIT 時: inner LLMClient を呼ばず、キャッシュから復元して返す。
    - MISS 時: inner を呼び、成功レスポンスのみキャッシュに保存。
    - 例外時: キャッシュに保存しない (次回再試行で上流リトライに任せる)。
    """

    def __init__(
        self,
        inner: LLMClient,
        cache: ResponseCache,
        *,
        provider: str,
        model: str,
    ) -> None:
        """CachingLLMClient を初期化する。

        Args:
            inner: ラップする実 LLMClient (AnthropicClient / GeminiClient)。
            cache: 値を保存する ResponseCache。
            provider: "anthropic" または "gemini" (キーに含める)。
            model: モデル名 (キーに含める)。
        """
        self._inner = inner
        self._cache = cache
        self._provider = provider
        self._model = model

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float,
    ) -> T:
        """構造化生成にキャッシュ層を被せる。

        HIT パスで JSON 復号 / Pydantic 検証に失敗した場合は該当 row を evict し、
        inner LLMClient を MISS として再呼び出しする (Self-Healing 原則)。

        Args:
            system_prompt: System Prompt テキスト。
            user_prompt: User Prompt テキスト。
            response_model: 出力の Pydantic モデルクラス。
            temperature: 生成時の Temperature。

        Returns:
            ``response_model`` のインスタンス。

        Raises:
            pydantic.ValidationError: inner の出力がスキーマに適合しない場合。
            anthropic.APIError / その他: API 呼び出しに失敗した場合 (上位に伝播)。
        """
        schema = response_model.model_json_schema()
        key = ResponseCache.make_key(
            provider=self._provider,
            model=self._model,
            kind="structured",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=None,
            response_schema=schema,
        )
        cached = self._cache.get(key)
        if cached is not None:
            try:
                envelope = json.loads(cached)
                payload = envelope["payload"]
                result_hit = response_model.model_validate(payload)
            except (json.JSONDecodeError, KeyError, pydantic.ValidationError) as exc:
                logger.warning(
                    "[cache] 破損 row を evict (model=%s response_model=%s err=%s)",
                    self._model,
                    response_model.__name__,
                    exc,
                )
                self._cache.delete(key)
            else:
                logger.info(
                    "[cache HIT] kind=structured model=%s response_model=%s",
                    self._model,
                    response_model.__name__,
                )
                return result_hit

        result = await self._inner.generate_structured(system_prompt, user_prompt, response_model, temperature)
        envelope = {"kind": "structured", "payload": result.model_dump(mode="json")}
        self._cache.put(key, json.dumps(envelope, ensure_ascii=False))
        logger.info(
            "[cache MISS] kind=structured model=%s response_model=%s",
            self._model,
            response_model.__name__,
        )
        return result

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int = 4096,
    ) -> str:
        """テキスト生成にキャッシュ層を被せる。

        HIT パスで JSON 復号 / payload 抽出に失敗した場合は該当 row を evict し、
        inner LLMClient を MISS として再呼び出しする (Self-Healing 原則)。

        Args:
            system_prompt: System Prompt テキスト。
            user_prompt: User Prompt テキスト。
            temperature: 生成時の Temperature。
            max_tokens: 最大トークン数。

        Returns:
            生成されたテキスト。

        Raises:
            ValueError / その他: API 呼び出しに失敗した場合 (上位に伝播)。
        """
        key = ResponseCache.make_key(
            provider=self._provider,
            model=self._model,
            kind="text",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=None,
        )
        cached = self._cache.get(key)
        if cached is not None:
            try:
                envelope = json.loads(cached)
                text_hit = envelope["payload"]
                if not isinstance(text_hit, str):
                    raise TypeError(f"text payload must be str, got {type(text_hit).__name__}")
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning(
                    "[cache] 破損 row を evict (model=%s kind=text err=%s)",
                    self._model,
                    exc,
                )
                self._cache.delete(key)
            else:
                logger.info("[cache HIT] kind=text model=%s", self._model)
                return text_hit

        result = await self._inner.generate_text(system_prompt, user_prompt, temperature, max_tokens)
        envelope = {"kind": "text", "payload": result}
        self._cache.put(key, json.dumps(envelope, ensure_ascii=False))
        logger.info("[cache MISS] kind=text model=%s", self._model)
        return result
