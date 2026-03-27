# タスクリスト: 全体精査に基づく包括的改善

## Critical 修正
- [x] #1 Temperature Decay バグ修正 (actor.py + pipeline.py)
- [x] #2 プロンプトハードコード修正 (memory.py + System_MemoryManager.md)
- [x] #3 デッドコード _update_memory_buffer 削除 (pipeline.py)

## High 修正
- [x] #4 revision_instruction サニタイズ (pipeline.py)
- [x] #5 Critic veto パステスト追加 (test_critic.py)
- [x] #6 _compute_inverse_estimation テスト追加 (test_critic.py)
- [x] #7 2層メモリ構造ドキュメント更新 (architecture.md, glossary.md)

## Medium 修正
- [x] #8 CSDGConfig.llm_api_key に Field(exclude=True) (config.py)
- [x] #10 unresolved_issue null チェック追加 (critic.py)
- [x] #11 _load_prompt 共通関数化 (prompt_loader.py + actor.py + critic.py)
- [x] #12 Any 型の正当化コメント (actor.py)
- [x] #13 pyproject.toml 二重定義解消
- [x] #14 依存パッケージバージョン上限追加
- [x] #15 config プロパティテスト追加 (test_config.py)

## Low 修正
- [x] #16 except Exception 絞り込み (critic_log.py, memory.py)
- [x] #17 docstring 追加 (critic.py)
- [x] #20 CLAUDE.md OpenAI → Anthropic 修正
- [x] #21 _format_long_term_context テスト追加 (test_actor.py)

## 却下
- #9 素材制限自動検出 (機能追加。別タスクで対応)
- #18 run_single_day 分割 (Info レベル。現状問題なし)
- #19 パストラバーサル対策 (CLI ツールとして低リスク)
- #22 visualization カバレッジ (低優先度)

## 検証
- [x] 313テスト全 Pass
- [x] mypy --strict クリーン
- [x] ruff エラーなし (既存の RUF002 2件は今回の変更外)
- [x] カバレッジ 89%
