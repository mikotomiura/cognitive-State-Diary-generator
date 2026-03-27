# 要件定義: OverloadedError のパイプラインレベルリトライ

## バグの症状
Anthropic API の OverloadedError (529) が発生すると、パイプラインが Day スキップ→3連続失敗→中断となり、日記が生成されない。

## 期待される動作
OverloadedError は一時的なサーバー過負荷であり、待機後にリトライすれば回復する。パイプラインは OverloadedError を他の例外と区別し、ウェイト付きリトライで同一Dayの処理を再試行すべき。

## 再現手順
Anthropic API が過負荷状態のときに `python -m csdg.main` を実行すると、全Dayが OverloadedError でスキップされパイプラインが中断する。

## 影響範囲
- `csdg/engine/pipeline.py` の `run()` メソッド

## 受け入れ条件
- [ ] OverloadedError 発生時にパイプラインレベルでウェイト付きリトライが実行される
- [ ] リトライ上限を超えた場合のみ Day スキップとなる
- [ ] 他の例外（RuntimeError 等）の挙動は変わらない
- [ ] テストが追加されている
