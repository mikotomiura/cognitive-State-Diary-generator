# Tasklist — feat-llm-response-cache

## 設計

- [x] `csdg/engine/llm_client.py` の現状把握 (file-finder で完了)
- [x] sqlite3 vs shelve の選定 → SQLite + WAL 採用
- [x] キャッシュキー正規化の設計 → temperature を `repr()` 文字列化、cache_format_version 含有
- [x] `generation_log.json` への `cached` フラグ追加方針 → V2 に先送り、V1 は logger.info で識別
- [x] `/reimagine` パターンで Codex 独立設計 (v2) を取得
- [x] v1 (Claude) vs v2 (Codex) 比較表作成 → v3 マージ案を採用 (`decisions.md` D-02)

## 実装 (構築フェーズ)

- [x] `csdg/engine/cache.py` 新規作成 (`ResponseCache` + `CachingLLMClient`)
- [x] `csdg/engine/llm_client.py` にキャッシュ層を組み込み → Decorator パターンで非変更
- [x] `csdg/main.py` に `--no-cache` フラグ追加
- [x] `csdg/main.py` にキャッシュ wrap ロジック追加 (Gemini fallback 時自動無効化含む)
- [x] `csdg/config.py` に `cache_enabled` / `cache_dir` 追加
- [x] `~/.cache/csdg/llm/` ディレクトリ自動作成 (`parents=True`)
- [x] DB ファイル権限 0600 (cross-review M-02)
- [x] `delete()` メソッド追加 (eviction 用)
- [x] HIT 復元失敗時の Self-Healing (evict + inner 再呼び出し / cross-review C-03/H-02)

## テスト (破壊フェーズ → 構築フェーズ)

- [x] `tests/test_llm_cache.py` 新規作成 (TDD Red 確認)
- [x] HIT / MISS の基本動作 (structured / text)
- [x] キー正規化 (同一プロンプトで HIT、各フィールド違いで MISS)
- [x] response_schema / temperature / max_tokens 違いで MISS
- [x] put / get / delete の永続化動作
- [x] 異常系: inner 例外時は cache 非保存 (text + structured)
- [x] 異常系: 破損 row の evict + 再呼び出し (text + structured)
- [x] DB ファイル権限 0600 検証
- [x] cache_format_version の直接ハッシュ照合 (cross-review W-03/L-01)

## 検証

- [x] `pytest tests/ -v -m "not e2e"` 緑 (583 件 Pass)
- [x] `mypy csdg/ --strict` 通過
- [x] `ruff check csdg/` 通過
- [x] `ruff format --check csdg/` 通過
- [x] `python -m csdg.main --dry-run` 疎通
- [x] `python -m csdg.main --dry-run --no-cache` 疎通
- [x] `python -m csdg.main --help` で `--no-cache` 表示確認

## レビュー (codex review フェーズ)

- [x] `code-reviewer` (Claude opus) による独立レビュー (CRITICAL 3 / WARNING 4 / INFO 3)
- [x] `codex-review` (gpt-5.5) による独立レビュー (HIGH 2 / MEDIUM 3 / LOW 1)
- [x] CRITICAL/HIGH 指摘 5 件を全て反映 (C-01 / C-02 / C-03+H-02 / H-01 / W-03+L-01)
- [x] MEDIUM 指摘を反映 (M-02 file mode 0600 / M-03 異常系テスト追加)
- [x] M-01 (phase 情報) は F-09-04 文言修正で V2 先送り

## ドキュメント

- [x] `docs/functional-design.md` F-09 追加 (-04 〜 -10 まで全 10 項目)
- [x] `docs/glossary.md` 「LLM レスポンスキャッシュ」用語追加
- [x] `docs/functional-design.md` §4.2 に `--no-cache` 追加

## 仕上げ

- [x] requirement.md 最終化
- [x] design.md 最終化 (v3 マージ案として確定)
- [x] design-v1-claude.md 保存 (アーカイブ)
- [x] design-v2-codex.md 保存 (アーカイブ)
- [x] decisions.md 作成 (D-01 reimagine / D-02 v3 マージ / D-03 schemas 非変更)
- [ ] コミットメッセージ準備
- [ ] `/finish-task` 実行
