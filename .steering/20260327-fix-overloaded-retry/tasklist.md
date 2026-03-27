# タスクリスト: OverloadedError のパイプラインレベルリトライ

## 実装タスク
- [x] pipeline.py: OverloadedError を個別キャッチし指数バックオフ付きリトライを追加
- [x] pipeline.py: asyncio, OverloadedError の import 追加
- [x] pipeline.py: 定数 _MAX_OVERLOAD_RETRIES, _OVERLOAD_BASE_DELAY_SEC 追加

## テストタスク
- [x] test_pipeline.py: 一時的 OverloadedError からの回復テスト
- [x] test_pipeline.py: consecutive_failures に加算されないことの検証
- [x] test_pipeline.py: リトライ上限超過時の Day スキップテスト
- [x] test_pipeline.py: 他の例外はリトライされないことの検証

## 検証タスク
- [x] 全テスト Pass (299/299)
- [x] mypy --strict Pass
- [x] ruff check Pass (既存の非クリティカル警告のみ)
