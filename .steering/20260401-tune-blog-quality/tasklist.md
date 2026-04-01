# タスクリスト: ブログ品質チューニング

## 実装タスク
- [x] Task 1: System_Persona.md にブログ情報追加
- [x] Task 2: Prompt_Generator.md の改修
- [x] Task 3: scenario.py のシナリオ全面改訂
- [x] Task 4: Prompt_Critic.md に面白さ評価基準追加
- [x] Task 5: critic.py の文字数チェック閾値更新
- [x] Task 6: config.py パラメータ確認（変更不要を確認済み）

## テストタスク
- [x] 文字数チェックの新規テスト追加 (TestCharCountValidation: 5テスト)
- [x] pytest tests/ -v で全Pass確認 (467 passed)
- [x] mypy strict 確認 (Success)
- [x] ruff check 確認 (All checks passed)

## コードレビュー指摘対応
- [x] C-01: veto閾値コメントを旧値(800-2000)から新値(300-500)に更新
- [x] C-02: タイトル行除外ロジックを `##` 以降の見出しにも対応 (re.match)
