# Design — feat-llm-response-cache

## アプローチ (v3 = v1 Claude + v2 Codex マージ)

`LLMClient` 抽象インターフェースの **Decorator パターン** で透過的にキャッシュ層をラップする。
本体実装 (`AnthropicClient` / `GeminiClient`) は変更せず、`CachingLLMClient` を新設して
`csdg/main.py` で wrap するか否かを `--no-cache` で切り替える。

ストアは Python 標準ライブラリの `sqlite3` を採用 + `PRAGMA journal_mode=WAL`。
- 単一ファイル / atomic writes / 並列読み書き安全
- 既存依存ゼロ
- 値は **TEXT JSON `{kind, payload}` 形式** (Codex 提案を採用、`.dump` での inspect 可能)

キャッシュキー設計: SHA-256 of canonical JSON of:
```
{
  "cache_format_version": "1",     # ← v2 提案。スキーマ変更時の旧キャッシュ全自動失効
  "provider": "anthropic" | "gemini",
  "model": str,
  "kind": "structured" | "text",
  "system_prompt": str,
  "user_prompt": str,
  "temperature": str,              # ← v2 提案。repr(float) で表現揺れ対策
  "max_tokens": int | null,        # text のみ。structured は null
  "response_schema": dict | null   # structured のみ。Pydantic JSON Schema 全体
                                   # (model_json_schema()) を含めることで field 変更を検出
}
```

含める判断:
- **temperature を repr() 文字列化して含める**: Phase 1 (固定 0.7) / Phase 3 (固定) では HIT、
  Phase 2 (retry で変動) では MISS。findings.md と整合。`repr(0.7)` で float 表現揺れ排除
- **`cache_format_version: "1"`**: 将来 schema 変更時に値を bump して旧キャッシュ全自動失効
- **`response_schema` を全文含める**: 同名 class の field 変更で誤復元するリスクを排除
- **`provider` / `model` は必須**: model 違いで誤 HIT を防ぐ
- **system_prompt / user_prompt は raw text**: 1 文字違えば別キー

保存値形式 (v2 採用):
```python
# structured
{"kind": "structured", "payload": response.model_dump(mode="json")}
# text
{"kind": "text", "payload": response_str}
```
復元: structured は `response_model.model_validate(payload)`、text は `payload` をそのまま返す。

## 検討した代替案

| 案 | 採否 | 理由 |
|---|---|---|
| **SQLite (stdlib)** | **採用** | 並列読み書き安全 / 単一ファイル / 既存依存ゼロ / atomic |
| `shelve` (stdlib) | 不採用 | 並列書き込みで破損リスク。BSD DB に依存し移植性に難 |
| `diskcache` (3rd party) | 不採用 | 高機能だが新規依存追加。SQLite で十分 |
| **Decorator パターン** | **採用** | 既存抽象 interface 非破壊。`--no-cache` で素直に外せる |
| 関数 decorator (`@lru_cache` 風) | 不採用 | async メソッドへの適用が煩雑。disk 永続化と相性悪い |
| LLMClient 内部にキャッシュ統合 | 不採用 | Anthropic / Gemini 両方に重複実装が必要、テストもスコープ広がる |
| **temperature を `repr()` 文字列化して含める** | **採用** | Phase 1+3 の HIT / Phase 2 確率変動を保つ + float 表現揺れ排除 (v2 採用) |
| temperature を float のままキーに | 不採用 | float 表現揺れで誤 MISS (0.7 vs 0.7000000001) |
| temperature を除外 (HIT 率優先) | 不採用 | Phase 2 で同じ retry が常に同じ結果を返すと品質悪化 |
| **`cache_format_version` をキーに含める** | **採用** (v2) | 将来のスキーマ変更で旧キャッシュ全自動失効 |
| **TEXT JSON 保存** | **採用** (v2) | sqlite で `.dump` 等の inspect 可能、復元の透明性 |
| BLOB 保存 | 不採用 | inspect 困難、エンコード明示性に劣る |
| **schemas.py 非変更** | **採用** | CLAUDE.md 禁止事項。`cached: bool` フラグ追加は V2 に先送り |
| GenerationRecord に `cached: bool` 追加 | 先送り | スキーマ移行が必要。Phase duration の自然短縮で `throughput_report.py` が効果を捉えれば V1 不要 |
| **stampede 対策の asyncio.Lock** | **V2 先送り** | V1 は同一 key の miss が並列発生する可能性低 (CSDG は逐次パイプライン)。Best-of-N 並列化の再開時に検討 |

## 変更ファイル一覧

| ファイル | 変更内容 | 影響範囲 |
|---|---|---|
| `csdg/engine/cache.py` (新規) | `ResponseCache` (sqlite3 wrapper) + `CachingLLMClient` (Decorator) | LLM 呼び出し全体 |
| `csdg/main.py` | `--no-cache` フラグ追加。client 構築後に `CachingLLMClient` で wrap (`--no-cache` 時は wrap せず) | CLI / pipeline 構築 |
| `csdg/config.py` | `cache_enabled: bool = True` / `cache_dir: str = "~/.cache/csdg/llm"` 追加 | 設定 |
| `tests/test_llm_cache.py` (新規) | `ResponseCache` + `CachingLLMClient` の単体テスト 12+ 件 | テスト |
| `tests/conftest.py` | `tmp_cache` フィクスチャ追加（任意） | テスト共通 |
| `docs/functional-design.md` | F-09 追加 / §4.2 に `--no-cache` 追加 | ✅ 完了 |
| `docs/glossary.md` | 「LLM レスポンスキャッシュ」用語追加 | ✅ 完了 |
| `docs/architecture.md` | データフロー節にキャッシュ層 | 任意（V2 で良い） |

**変更しないファイル**:
- `csdg/schemas.py` — 破壊的変更禁止（CLAUDE.md）
- `csdg/engine/llm_client.py` — Decorator で外部から wrap するため非変更
- `prompts/*.md` — 変更なし
- `csdg/engine/actor.py`, `critic.py`, `memory.py`, `pipeline.py` — caller 側は LLMClient interface しか触らない

## データフロー

```
[caller] (actor / critic / memory)
    ↓ generate_structured() / generate_text()
[CachingLLMClient]  ← --no-cache 時は中間層を外して直接 inner へ
    ↓ key = sha256(canonical_json(...))
    ↓ cache.get(key)? ──HIT──→ deserialize → return (logger.info "[cache HIT]")
    ↓ MISS
[inner LLMClient (Anthropic / Gemini)]
    ↓ API 呼び出し
    ← response
[CachingLLMClient]
    ↓ cache.put(key, serialized_response)
    → return (logger.info "[cache MISS] key=... model=...")
```

## ResponseCache クラス設計

```python
class ResponseCache:
    """SQLite-backed KV cache for LLM responses.

    Thread-safe via sqlite3 connection per call (short-lived connections).
    """
    def __init__(self, db_path: Path) -> None: ...

    def get(self, key: str) -> bytes | None: ...

    def put(self, key: str, value: bytes) -> None: ...

    def stats(self) -> dict[str, int]:
        """Return {entries: int, total_bytes: int} for diagnostics."""

    @staticmethod
    def make_key(
        provider: str,
        model: str,
        kind: Literal["structured", "text"],
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int | None,
        response_schema_hash: str | None,
    ) -> str: ...
```

## CachingLLMClient クラス設計

```python
class CachingLLMClient(LLMClient):
    def __init__(self, inner: LLMClient, cache: ResponseCache, *, provider: str, model: str) -> None:
        self._inner = inner
        self._cache = cache
        self._provider = provider  # "anthropic" / "gemini"
        self._model = model

    async def generate_structured(self, system_prompt, user_prompt, response_model, temperature) -> T:
        schema_hash = sha256(json.dumps(response_model.model_json_schema(), sort_keys=True).encode())
        key = ResponseCache.make_key(
            provider=self._provider, model=self._model, kind="structured",
            system_prompt=system_prompt, user_prompt=user_prompt,
            temperature=temperature, max_tokens=None, response_schema_hash=schema_hash.hexdigest(),
        )
        cached = self._cache.get(key)
        if cached is not None:
            logger.info("[cache HIT] kind=structured model=%s response_model=%s",
                        self._model, response_model.__name__)
            return response_model.model_validate_json(cached)
        result = await self._inner.generate_structured(system_prompt, user_prompt, response_model, temperature)
        self._cache.put(key, result.model_dump_json().encode())
        logger.info("[cache MISS] kind=structured model=%s response_model=%s",
                    self._model, response_model.__name__)
        return result

    async def generate_text(self, system_prompt, user_prompt, temperature, max_tokens=4096) -> str:
        key = ResponseCache.make_key(...)
        cached = self._cache.get(key)
        if cached is not None: return cached.decode()
        result = await self._inner.generate_text(...)
        self._cache.put(key, result.encode())
        return result
```

## main.py の組み込み

```python
client: LLMClient
if config.llm_provider == "gemini":
    client = GeminiClient(...)
else:
    client = AnthropicClient(...)

if not args.no_cache and config.cache_enabled:
    cache_dir = Path(config.cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = ResponseCache(cache_dir / "cache.sqlite")
    client = CachingLLMClient(client, cache, provider=config.llm_provider, model=config.llm_model)
    logger.info("[cache] enabled at %s", cache_dir / "cache.sqlite")
else:
    logger.info("[cache] disabled (--no-cache or config.cache_enabled=False)")
```

## テスト戦略

`tests/test_llm_cache.py` (新規):

1. `ResponseCache.make_key` 正規化テスト
   - 同一入力 → 同一キー
   - temperature 0.7 vs 0.71 → 別キー
   - dict 順序不変（canonical JSON）
   - response_schema_hash あり/なしで別キー

2. `ResponseCache` get/put テスト（tmp_path で sqlite ファイル分離）
   - put → get で同値返却
   - 未登録キー → None
   - 大容量バイト列でも動作

3. `CachingLLMClient` テスト（AsyncMock で inner stub）
   - 1 回目: MISS → inner 呼び出し → cache.put
   - 2 回目: HIT → inner 呼び出し回数 0
   - structured / text 両方で同様
   - response_model 違いで HIT しない
   - temperature 違いで HIT しない

4. main.py の `--no-cache` 統合テスト
   - bypass 時に CachingLLMClient で wrap されない（dry-run で確認可能）

5. 既存テスト 551 件のリグレッションがゼロ

## リスク / トレードオフ

| リスク | 対策 |
|---|---|
| キャッシュ汚染（誤った結果が永続） | `--no-cache` で逃げ道。手動削除手順を docs に明記 |
| ストア肥大化（TTL なし） | チューニング作業中は問題なし。本番で気になれば `LIMIT` + LRU 退避を V2 で |
| sqlite ロック競合（並列書き込み） | sqlite はデフォルトで file-level lock。Best-of-N 並列なら問題なし。WAL モードで READ 競合を緩和可 |
| Pydantic モデル変更で旧キャッシュ誤適用 | `response_schema_hash` をキーに含めることで自動的に別キー化 |
| Phase 2 で retry temperature が変動するため HIT 率低 | 設計通り（findings.md と整合）。本番品質維持のためむしろ望ましい |
| `generation_log.json` の Phase duration が不自然に短く見える | F-09-04 の logger 出力で識別可能。throughput_report.py は短縮を素直に検出 |

## 後方互換性

- 既存テスト 551 件: cache 無効化 (キャッシュ層を通さない場合) で完全互換。フィクスチャ修正不要
- main.py の引数: 新規フラグ `--no-cache` のみ追加（既定で cache 有効）。CI / 既存スクリプトは
  ノイズなく動作する（出力時間が短くなる方向のみ）
- `~/.cache/csdg/` は新規ディレクトリで既存作業に干渉しない
