# タスクリスト: レビュー Critical 3件の修正

## 実装タスク
- [x] C-01: ShortTermMemory.limit_entries を model_validator に変更し window_size 連動
- [x] C-02: MemoryManager に temperature_final パラメータ追加、マジックナンバー除去
- [x] C-03: Critic._build_critic_prompt と未使用フィールドを削除、docstring 追加

## テストタスク
- [x] TestShortTermMemoryWindowSize 追加（Red → Green 確認済み）
- [x] 既存テスト _build_critic_prompt 参照を削除

## 検証
- [x] 322テスト全 Pass
- [x] mypy --strict クリーン
- [x] ruff check クリーン
