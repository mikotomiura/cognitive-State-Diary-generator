# Design v2 — Codex (gpt-5.5, low reasoning) 独立提案

**取得日時**: 2026-05-08
**取得方法**: `scripts/run-codex-consult.sh` 経由 (read-only sandbox / low reasoning)
**入力**: `requirement.md` の抜粋 + 既存 `LLMClient` interface + 制約条件
**Codex には Claude 側の v1 design.md は渡していない (anchor バイアス排除)**

---

## 1. アーキテクチャ

`LLMClient` の **Decorator** を推奨。

```python
class CachedLLMClient(LLMClient):
    def __init__(self, inner: LLMClient, cache: LLMCache, enabled: bool = True):
        self.inner = inner
        self.cache = cache
        self.enabled = enabled
```

既存の `LLMClient` interface / `AnthropicClient` / `GeminiClient` を変更せずに前段へ差し込める。CLI 側で `--no-llm-cache` などで `enabled=False` にするか、Decorator を挟まない構成にできる。

## 2. キャッシュキー設計

JSON canonicalize した入力を `sha256`。含めるべきフィールド:

- method: `generate_text` / `generate_structured`
- system_prompt
- user_prompt
- temperature
- `max_tokens` (text のみ)
- response model identity (structured のみ):
  - `response_model.__module__`
  - `response_model.__qualname__`
  - `response_model.model_json_schema()`
- **cache format version**
- **optional**: provider/model name (`LLMClient` が外部に公開していれば)

temperature は float の表現揺れを避けるため `repr(temperature)` で文字列化。

Pydantic v2 の schema 変更対応として、`model_json_schema()` を含めるのが重要。モデル名だけだと同名 class の field 変更で古い JSON を誤復元する危険。

保存値:
```json
{
  "kind": "structured",
  "payload": response.model_dump(mode="json")
}
```
復元: `response_model.model_validate(payload)`。text は plain string を JSON に包んで保存。

## 3. ストレージ

**sqlite3** 推奨。

- stdlib / 単一ファイル / concurrent read に強い
- transaction が明確 / `UNIQUE(key)` + `INSERT OR REPLACE`
- `PRAGMA journal_mode=WAL` で並列実行に比較的強い

```sql
CREATE TABLE llm_cache (
  key TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  value_json TEXT NOT NULL,
  created_at REAL NOT NULL
);
```

sqlite3 は同期 API なので、async 関数内では短い DB 操作に限定。LLM 呼び出し中に DB lock を保持しない。必要ならプロセス内 `asyncio.Lock` で write 保護。

`shelve` / `dbm` は並列アクセス・破損耐性・migration 面で sqlite3 に劣る。

## 4. 代替案と不採用理由

- **AnthropicClient / GeminiClient 内部に統合**: provider ごとに重複実装、既存実装の破壊リスク、CLI bypass も散らばる
- **関数 wrapper**: 呼び出し側すべてを変更する必要、漏れやすい、抽象の利点を活かせない
- **JSON ファイル 1 key 1 file**: 実装は単純だが、大量ファイル / atomic write / cleanup / 並列 write 制御が面倒、テストもしづらい

## 5. 落とし穴

- **キャッシュ汚染**: provider/model/version が異なるのに同一キー扱いは危険 → model 名をキーに含める
- **失敗レスポンス保存禁止**: exception / validation error は保存しない
- **async 競合 (stampede)**: 同一 key の miss が並列発生すると二重 LLM 呼び出しになる。許容するか、key ごとの `asyncio.Lock` を入れる
- **Pydantic 復元**: `model_dump_json()` の文字列をそのまま返さず、必ず `response_model.model_validate()` で復元
- **非決定性**: temperature が同じでも provider 側は完全決定的とは限らない。用途を tuning 高速化に限定し、CLI bypass を必ず用意
