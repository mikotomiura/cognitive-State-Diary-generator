"""csdg/engine/cache.py のテスト。

ResponseCache (sqlite3 KV ストア) と CachingLLMClient (LLMClient Decorator) の挙動を検証する。
F-09 (LLM レスポンスキャッシュ) の受け入れ基準に対応。

テストは AAA パターン + パラメタライズで構成。tmp_path フィクスチャで sqlite ファイルを分離。
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from csdg.engine.cache import CachingLLMClient, ResponseCache
from csdg.engine.llm_client import LLMClient

if TYPE_CHECKING:
    from pathlib import Path


class _SampleStructured(BaseModel):
    """テスト用の Pydantic モデル。"""

    name: str
    score: int


class _SampleStructuredV2(BaseModel):
    """field 構成が _SampleStructured と異なる別モデル。schema_hash が別になることを検証する。"""

    name: str
    score: int
    extra: str = "default"


# --- ResponseCache.make_key の正規化テスト ---


class TestMakeKey:
    """ResponseCache.make_key の正規化動作を検証する。"""

    def _base_kwargs(self) -> dict[str, object]:
        return {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "kind": "structured",
            "system_prompt": "You are a helpful assistant.",
            "user_prompt": "Hello",
            "temperature": 0.7,
            "max_tokens": None,
            "response_schema": {"type": "object", "properties": {}},
        }

    def test_same_input_same_key(self) -> None:
        """同一入力は同一キーを返す。"""
        key1 = ResponseCache.make_key(**self._base_kwargs())  # type: ignore[arg-type]
        key2 = ResponseCache.make_key(**self._base_kwargs())  # type: ignore[arg-type]

        assert key1 == key2

    def test_temperature_repr_normalization(self) -> None:
        """temperature は repr() 文字列化されているため 0.7 == 0.7 で同一キー。"""
        kwargs1 = self._base_kwargs()
        kwargs1["temperature"] = 0.7
        kwargs2 = self._base_kwargs()
        kwargs2["temperature"] = 0.7

        assert ResponseCache.make_key(**kwargs1) == ResponseCache.make_key(**kwargs2)  # type: ignore[arg-type]

    def test_temperature_difference_yields_different_key(self) -> None:
        """temperature が違えば別キー。"""
        kwargs_a = self._base_kwargs()
        kwargs_a["temperature"] = 0.7
        kwargs_b = self._base_kwargs()
        kwargs_b["temperature"] = 0.6

        assert ResponseCache.make_key(**kwargs_a) != ResponseCache.make_key(**kwargs_b)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "field,value_a,value_b",
        [
            ("provider", "anthropic", "gemini"),
            ("model", "claude-sonnet-4-20250514", "gemini-2.0-flash"),
            ("kind", "structured", "text"),
            ("system_prompt", "You are A.", "You are B."),
            ("user_prompt", "Hello", "Hi"),
            ("max_tokens", None, 4096),
        ],
    )
    def test_field_difference_yields_different_key(self, field: str, value_a: object, value_b: object) -> None:
        """各フィールドの違いで別キーになる。"""
        kwargs_a = self._base_kwargs()
        kwargs_a[field] = value_a
        kwargs_b = self._base_kwargs()
        kwargs_b[field] = value_b

        assert ResponseCache.make_key(**kwargs_a) != ResponseCache.make_key(**kwargs_b)  # type: ignore[arg-type]

    def test_response_schema_difference_yields_different_key(self) -> None:
        """response_schema の field 構成が違えば別キー。"""
        kwargs_a = self._base_kwargs()
        kwargs_a["response_schema"] = _SampleStructured.model_json_schema()
        kwargs_b = self._base_kwargs()
        kwargs_b["response_schema"] = _SampleStructuredV2.model_json_schema()

        assert ResponseCache.make_key(**kwargs_a) != ResponseCache.make_key(**kwargs_b)  # type: ignore[arg-type]

    def test_cache_format_version_returns_64_hex(self) -> None:
        """make_key の戻り値は 64 文字の SHA-256 hex 文字列である。"""
        key = ResponseCache.make_key(**self._base_kwargs())  # type: ignore[arg-type]

        assert isinstance(key, str)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_cache_format_version_in_canonical_payload(self) -> None:
        """make_key が _CACHE_FORMAT_VERSION をハッシュ前 payload に含める。

        version を bump した時に旧キャッシュが自動失効することを直接検証する
        (cross-review W-03/L-01 反映)。
        """
        import hashlib
        import json

        from csdg.engine.cache import _CACHE_FORMAT_VERSION

        kwargs = self._base_kwargs()
        actual_key = ResponseCache.make_key(**kwargs)  # type: ignore[arg-type]

        # 期待する canonical payload (version="1") を再現してハッシュを照合
        expected_payload = {
            "cache_format_version": _CACHE_FORMAT_VERSION,
            "provider": kwargs["provider"],
            "model": kwargs["model"],
            "kind": kwargs["kind"],
            "system_prompt": kwargs["system_prompt"],
            "user_prompt": kwargs["user_prompt"],
            "temperature": repr(kwargs["temperature"]),
            "max_tokens": kwargs["max_tokens"],
            "response_schema": kwargs["response_schema"],
        }
        expected_key = hashlib.sha256(
            json.dumps(expected_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        assert actual_key == expected_key

        # version が違えば別キーになる
        bumped = dict(expected_payload, cache_format_version="999")
        bumped_key = hashlib.sha256(json.dumps(bumped, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        assert actual_key != bumped_key


# --- ResponseCache get/put テスト ---


class TestResponseCache:
    """ResponseCache の get/put 永続化動作を検証する。"""

    def test_put_and_get_roundtrip(self, tmp_path: Path) -> None:
        """put した値が get で取り出せる。"""
        cache = ResponseCache(tmp_path / "cache.sqlite")
        cache.put("key1", '{"kind": "text", "payload": "hello"}')

        result = cache.get("key1")

        assert result == '{"kind": "text", "payload": "hello"}'

    def test_get_unknown_key_returns_none(self, tmp_path: Path) -> None:
        """未登録キーは None を返す。"""
        cache = ResponseCache(tmp_path / "cache.sqlite")

        result = cache.get("nonexistent")

        assert result is None

    def test_put_overwrites_existing_key(self, tmp_path: Path) -> None:
        """既存キーへの put は上書き。"""
        cache = ResponseCache(tmp_path / "cache.sqlite")
        cache.put("key1", '{"kind": "text", "payload": "first"}')
        cache.put("key1", '{"kind": "text", "payload": "second"}')

        result = cache.get("key1")

        assert result == '{"kind": "text", "payload": "second"}'

    def test_persistent_across_instances(self, tmp_path: Path) -> None:
        """別インスタンスでも同じファイルを開けば値が見える。"""
        db_path = tmp_path / "cache.sqlite"
        cache1 = ResponseCache(db_path)
        cache1.put("key1", '{"kind": "text", "payload": "stored"}')

        cache2 = ResponseCache(db_path)
        result = cache2.get("key1")

        assert result == '{"kind": "text", "payload": "stored"}'

    def test_large_payload(self, tmp_path: Path) -> None:
        """大容量 payload (10KB) でも動作する。"""
        cache = ResponseCache(tmp_path / "cache.sqlite")
        large_value = '{"kind": "text", "payload": "' + ("x" * 10000) + '"}'
        cache.put("key1", large_value)

        result = cache.get("key1")

        assert result == large_value

    def test_db_directory_auto_created(self, tmp_path: Path) -> None:
        """親ディレクトリが存在しなくても自動作成される。"""
        nested_path = tmp_path / "nested" / "dir" / "cache.sqlite"

        cache = ResponseCache(nested_path)
        cache.put("key1", '{"kind": "text", "payload": "ok"}')

        assert nested_path.exists()
        assert cache.get("key1") == '{"kind": "text", "payload": "ok"}'


# --- CachingLLMClient HIT / MISS テスト ---


@pytest.fixture()
def cache_for_test(tmp_path: Path) -> ResponseCache:
    """テスト用 ResponseCache (tmp_path で分離)。"""
    return ResponseCache(tmp_path / "cache.sqlite")


@pytest.fixture()
def inner_mock() -> AsyncMock:
    """LLMClient の inner mock。"""
    return AsyncMock(spec=LLMClient)


class TestCachingLLMClientStructured:
    """CachingLLMClient.generate_structured の HIT/MISS 動作。"""

    @pytest.mark.asyncio
    async def test_first_call_misses_and_invokes_inner(
        self, cache_for_test: ResponseCache, inner_mock: AsyncMock
    ) -> None:
        """1 回目は MISS で inner が呼ばれる。"""
        inner_mock.generate_structured.return_value = _SampleStructured(name="alice", score=42)
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        result = await client.generate_structured(
            system_prompt="sys", user_prompt="user", response_model=_SampleStructured, temperature=0.7
        )

        assert result == _SampleStructured(name="alice", score=42)
        inner_mock.generate_structured.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_second_call_hits_and_skips_inner(self, cache_for_test: ResponseCache, inner_mock: AsyncMock) -> None:
        """2 回目は HIT で inner は呼ばれない。"""
        inner_mock.generate_structured.return_value = _SampleStructured(name="alice", score=42)
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        # 1 回目: MISS
        await client.generate_structured(
            system_prompt="sys", user_prompt="user", response_model=_SampleStructured, temperature=0.7
        )
        inner_mock.generate_structured.reset_mock()

        # 2 回目: HIT
        result = await client.generate_structured(
            system_prompt="sys", user_prompt="user", response_model=_SampleStructured, temperature=0.7
        )

        assert result == _SampleStructured(name="alice", score=42)
        inner_mock.generate_structured.assert_not_called()

    @pytest.mark.asyncio
    async def test_different_response_model_misses(self, cache_for_test: ResponseCache, inner_mock: AsyncMock) -> None:
        """response_model が違えば HIT しない。"""
        inner_mock.generate_structured.side_effect = [
            _SampleStructured(name="alice", score=42),
            _SampleStructuredV2(name="bob", score=10, extra="v2"),
        ]
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        await client.generate_structured(
            system_prompt="sys", user_prompt="user", response_model=_SampleStructured, temperature=0.7
        )
        await client.generate_structured(
            system_prompt="sys", user_prompt="user", response_model=_SampleStructuredV2, temperature=0.7
        )

        assert inner_mock.generate_structured.await_count == 2

    @pytest.mark.asyncio
    async def test_different_temperature_misses(self, cache_for_test: ResponseCache, inner_mock: AsyncMock) -> None:
        """temperature が違えば HIT しない。"""
        inner_mock.generate_structured.return_value = _SampleStructured(name="alice", score=42)
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        await client.generate_structured(
            system_prompt="sys", user_prompt="user", response_model=_SampleStructured, temperature=0.7
        )
        await client.generate_structured(
            system_prompt="sys", user_prompt="user", response_model=_SampleStructured, temperature=0.6
        )

        assert inner_mock.generate_structured.await_count == 2


class TestCachingLLMClientText:
    """CachingLLMClient.generate_text の HIT/MISS 動作。"""

    @pytest.mark.asyncio
    async def test_first_call_misses_and_invokes_inner(
        self, cache_for_test: ResponseCache, inner_mock: AsyncMock
    ) -> None:
        inner_mock.generate_text.return_value = "今日は晴れだった。"
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        result = await client.generate_text(system_prompt="sys", user_prompt="user", temperature=0.7, max_tokens=4096)

        assert result == "今日は晴れだった。"
        inner_mock.generate_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_second_call_hits_and_skips_inner(self, cache_for_test: ResponseCache, inner_mock: AsyncMock) -> None:
        inner_mock.generate_text.return_value = "今日は晴れだった。"
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        await client.generate_text(system_prompt="sys", user_prompt="user", temperature=0.7, max_tokens=4096)
        inner_mock.generate_text.reset_mock()

        result = await client.generate_text(system_prompt="sys", user_prompt="user", temperature=0.7, max_tokens=4096)

        assert result == "今日は晴れだった。"
        inner_mock.generate_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_different_max_tokens_misses(self, cache_for_test: ResponseCache, inner_mock: AsyncMock) -> None:
        inner_mock.generate_text.return_value = "result"
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        await client.generate_text(system_prompt="sys", user_prompt="user", temperature=0.7, max_tokens=2048)
        await client.generate_text(system_prompt="sys", user_prompt="user", temperature=0.7, max_tokens=4096)

        assert inner_mock.generate_text.await_count == 2


class TestCachingLLMClientErrorHandling:
    """CachingLLMClient の異常系。"""

    @pytest.mark.asyncio
    async def test_inner_exception_not_cached_text(self, cache_for_test: ResponseCache, inner_mock: AsyncMock) -> None:
        """generate_text の inner 例外は cache に記録しない。次回も再試行される。"""
        inner_mock.generate_text.side_effect = [
            RuntimeError("API failure"),
            "second try result",
        ]
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        with pytest.raises(RuntimeError):
            await client.generate_text(system_prompt="sys", user_prompt="user", temperature=0.7, max_tokens=4096)

        # 例外を保存していなければ、2 回目は再度 inner が呼ばれて成功する
        result = await client.generate_text(system_prompt="sys", user_prompt="user", temperature=0.7, max_tokens=4096)

        assert result == "second try result"
        assert inner_mock.generate_text.await_count == 2

    @pytest.mark.asyncio
    async def test_inner_exception_not_cached_structured(
        self, cache_for_test: ResponseCache, inner_mock: AsyncMock
    ) -> None:
        """generate_structured の inner 例外も cache に記録しない (cross-review I-02 反映)。"""
        inner_mock.generate_structured.side_effect = [
            RuntimeError("API failure"),
            _SampleStructured(name="bob", score=99),
        ]
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        with pytest.raises(RuntimeError):
            await client.generate_structured(
                system_prompt="sys",
                user_prompt="user",
                response_model=_SampleStructured,
                temperature=0.7,
            )

        result = await client.generate_structured(
            system_prompt="sys",
            user_prompt="user",
            response_model=_SampleStructured,
            temperature=0.7,
        )

        assert result == _SampleStructured(name="bob", score=99)
        assert inner_mock.generate_structured.await_count == 2

    @pytest.mark.asyncio
    async def test_corrupted_row_evicted_and_inner_called_text(
        self, cache_for_test: ResponseCache, inner_mock: AsyncMock
    ) -> None:
        """壊れた cache row (不正 JSON) は evict し inner を再呼び出し (Self-Healing)。"""
        inner_mock.generate_text.return_value = "fresh result"
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        # 1 回目: MISS で正しい値が保存される
        await client.generate_text(system_prompt="sys", user_prompt="user", temperature=0.7, max_tokens=4096)
        # キーを再現して破損 JSON を直接書き込む
        key = ResponseCache.make_key(
            provider="anthropic",
            model="claude-sonnet-4",
            kind="text",
            system_prompt="sys",
            user_prompt="user",
            temperature=0.7,
            max_tokens=4096,
            response_schema=None,
        )
        cache_for_test.put(key, "{this is not valid json}")
        inner_mock.generate_text.reset_mock()
        inner_mock.generate_text.return_value = "recovered result"

        # 2 回目: 破損 row を evict → inner を再呼び出し
        result = await client.generate_text(system_prompt="sys", user_prompt="user", temperature=0.7, max_tokens=4096)

        assert result == "recovered result"
        inner_mock.generate_text.assert_awaited_once()
        # 破損 row は新しい正常 row で置き換わっているはず
        stored = cache_for_test.get(key)
        assert stored is not None
        assert "recovered result" in stored

    @pytest.mark.asyncio
    async def test_corrupted_row_evicted_and_inner_called_structured(
        self, cache_for_test: ResponseCache, inner_mock: AsyncMock
    ) -> None:
        """structured でも破損 row は evict + 再呼び出し。"""
        inner_mock.generate_structured.return_value = _SampleStructured(name="alice", score=42)
        client = CachingLLMClient(inner_mock, cache_for_test, provider="anthropic", model="claude-sonnet-4")

        # 1 回目: MISS
        await client.generate_structured(
            system_prompt="sys",
            user_prompt="user",
            response_model=_SampleStructured,
            temperature=0.7,
        )
        # 破損: payload が schema に合わない値で上書き
        schema = _SampleStructured.model_json_schema()
        key = ResponseCache.make_key(
            provider="anthropic",
            model="claude-sonnet-4",
            kind="structured",
            system_prompt="sys",
            user_prompt="user",
            temperature=0.7,
            max_tokens=None,
            response_schema=schema,
        )
        cache_for_test.put(key, '{"kind": "structured", "payload": {"unexpected": "field"}}')
        inner_mock.generate_structured.reset_mock()
        inner_mock.generate_structured.return_value = _SampleStructured(name="bob", score=10)

        result = await client.generate_structured(
            system_prompt="sys",
            user_prompt="user",
            response_model=_SampleStructured,
            temperature=0.7,
        )

        assert result == _SampleStructured(name="bob", score=10)
        inner_mock.generate_structured.assert_awaited_once()


class TestResponseCacheDelete:
    """ResponseCache.delete のテスト (eviction 用)。"""

    def test_delete_removes_key(self, tmp_path: Path) -> None:
        cache = ResponseCache(tmp_path / "cache.sqlite")
        cache.put("k1", '{"kind": "text", "payload": "v"}')

        cache.delete("k1")

        assert cache.get("k1") is None

    def test_delete_nonexistent_key_is_noop(self, tmp_path: Path) -> None:
        cache = ResponseCache(tmp_path / "cache.sqlite")

        # 存在しないキーの delete は例外を投げない
        cache.delete("nonexistent")

        assert cache.get("nonexistent") is None


class TestResponseCacheFilePermissions:
    """DB ファイル権限のテスト (cross-review M-02 反映)。"""

    def test_db_file_mode_is_owner_only(self, tmp_path: Path) -> None:
        """DB ファイルは owner read/write のみ (0600) に設定される。"""
        import stat
        import sys

        if sys.platform == "win32":
            pytest.skip("Windows では POSIX permission をスキップ")

        db_path = tmp_path / "cache.sqlite"
        ResponseCache(db_path)

        mode = stat.S_IMODE(db_path.stat().st_mode)
        assert mode == 0o600
