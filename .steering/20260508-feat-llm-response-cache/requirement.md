# Requirement — feat-llm-response-cache

## 背景

前タスク `20260508-tuning-rotation-throughput` の `findings.md` で、プロンプトチューニング 1 サイクル
（7 Day 生成 = 約 270 秒）のうち **Phase 2 (Content Generation) が 57% を占める主ボトルネック** であり、
かつ **6 プロンプト中 5 つ (Critic / MemoryExtract / StateUpdate / MemoryManager / Persona) が全 run で
同一ハッシュ** であることが判明した。Generator.md ですら run 間で重複しているケースがある。

つまり「プロンプト編集 → 再走」のチューニング作業では、編集していないプロンプトの LLM 呼び出しが
**毎回不要に再実行されている**。LLM レスポンスキャッシュを導入すれば、Phase 1 (StateUpdate / Memory) と
Phase 3 (Critic) の大半がキャッシュ HIT で実質 0 秒になる見込み（**1 サイクル 270s → 110-150s に短縮**）。

これは findings.md §6 で **採用案 1st (ROI ★★★)** として推奨され、後続タスク名候補として
`feat/llm-response-cache` が明示されている。Memory feedback「プロンプトチューニングは構造的限界、
コード側の動的制約に切り替えよ」とも整合する（チューニング作業自体の構造的高速化）。

## ゴール

- [ ] `csdg/engine/llm_client.py` の前段に disk-based KV キャッシュ層を追加する
- [ ] キャッシュキーは `(prompt_text_hash, model, temperature, max_tokens, response_format, ...)` の
      正規化ハッシュとし、同一入力で同一出力を返す
- [ ] `--no-cache` CLI フラグでキャッシュを bypass できる（本番生成時 / cache 検証時）
- [ ] キャッシュストアは `~/.cache/csdg/llm/` 配下に配置（プロジェクトディレクトリ外）
- [ ] チューニングサイクル時間が実測で短縮していることを `scripts/throughput_report.py` で確認する
      （目標: 編集しなかったプロンプトの呼び出しがキャッシュ HIT する）
- [ ] `tests/test_llm_cache.py` で AAA + パラメタライズで挙動を検証

## 非ゴール

- 本番生成 (production diary generation) の確率変動を **失わせない**: temperature を含むキーで
  HIT 率は下がるが、再現性のあるチューニング向けの仕組みであることを優先
- Phase 2 (Content Generation) 自体の高速化 — Generator は temperature が変動するため HIT 率が低い
- Best-of-N 並列化 (findings.md §6 で当面ペンディング)
- Day 単位部分実行 / state 復元 (後続タスク `feat/day-resume-from-cache` のスコープ)
- 固定 seed / temperature=0 評価モード (後続タスク `feat/deterministic-eval-mode` のスコープ)
- API コスト (token / dollar) 集計
- キャッシュ自動失効 (TTL) — 手動 `rm -rf ~/.cache/csdg/llm/` で十分

## 制約 / 前提条件

- `csdg/schemas.py` の破壊的変更は禁止（CLAUDE.md 禁止事項 / 既存テスト 551 件と整合性が崩れる）
- プロンプトファイル (`prompts/*.md`) は変更しない
- 既存テスト 551 件 (`pytest -m "not e2e"`) は緑のまま
- LLM クライアントの API シグネチャは破壊的変更しない（caller 側の改修を最小化）
- キャッシュ HIT 時もログ (`generation_log.json`) には呼び出しが記録される必要がある
  （計測連続性のため。ただし `cached: true` フラグで識別可能にする）
- ストアの選定は **stdlib のみ** (sqlite3 / shelve) を優先。新規依存追加は最終手段
- 機密情報 (API キー / persona 内容) はキャッシュ自体には保存されるが、
  `~/.cache/csdg/` はユーザーローカル領域なので外部送信リスクは無し
- 関連: `20260508-tuning-rotation-throughput/findings.md` (採用根拠) /
  `20260507-best-of-n-parallel/design.md` (Best-of-N との関係)

## 完了条件 (Definition of Done)

- [ ] `pytest tests/ -v -m "not e2e"` 緑（551+ 件）
- [ ] `mypy csdg/ --strict` 通過
- [ ] `ruff check csdg/` 通過
- [ ] `ruff format --check csdg/` 通過
- [ ] `python -m csdg.main --dry-run` 疎通成功
- [ ] `python -m csdg.main` を 2 回連続実行し、2 回目の Phase 1 / Phase 3 がキャッシュ HIT で
      短縮されていることを `scripts/throughput_report.py` で確認
- [ ] `--no-cache` で 1 回目同等の時間で完走することを確認
- [ ] `docs/architecture.md` のデータフロー節にキャッシュ層の説明を追記
- [ ] `tasklist.md` のチェックがすべて埋まっている
