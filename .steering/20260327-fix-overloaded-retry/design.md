# 設計: OverloadedError のパイプラインレベルリトライ

## 原因分析
- SDK レベル: `max_retries=5` でリトライ（指数バックオフ）するが、5回全て失敗すると `OverloadedError` を raise
- パイプライン: `except Exception` で全例外をキャッチし Day スキップ。OverloadedError も RuntimeError も同じ扱い
- 結果: API 過負荷が続くと 3Day 連続スキップでパイプライン中断

## 修正アプローチ
`run()` メソッドの例外ハンドリングで `OverloadedError` を個別にキャッチし、指数バックオフ付きリトライで同一Dayを再試行する。

### 実装詳細
1. `anthropic.OverloadedError` を import
2. `run()` の for ループ内で、同一 Day に対するリトライループを追加
3. リトライ間隔: 指数バックオフ（30s, 60s, 120s）
4. 最大リトライ回数: 3回（定数 `_MAX_OVERLOAD_RETRIES`）
5. リトライ上限を超えた場合のみ consecutive_failures をインクリメント

## 変更対象ファイル
| ファイル | 変更内容 |
|---|---|
| `csdg/engine/pipeline.py` | OverloadedError のリトライロジック追加 |
| `tests/test_pipeline.py` | OverloadedError リトライのテスト追加 |
