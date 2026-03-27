# 設計: prev_endings 注入による余韻反復防止

## 実装アプローチ
直近3Dayの末尾段落（余韻）を抽出・蓄積し、Prompt_Generator.md に「過去の余韻（使用済み）」セクションとして注入する。

## 変更対象ファイル
| ファイル | 変更内容 |
|---|---|
| csdg/engine/pipeline.py | _extract_ending ヘルパー追加, prev_endings 蓄積・受け渡し |
| csdg/engine/actor.py | prev_endings パラメータ追加, プロンプト構築 |
| prompts/Prompt_Generator.md | {prev_endings} プレースホルダ追加 |
| tests/test_pipeline.py | TestExtractEnding, TestPrevEndingsTracking 追加 |
| tests/test_actor.py | TestPrevEndings 追加, フィクスチャ更新 |

## 代替案と選定理由
- 案A: prev_diaryの末尾のみ注入 → 非連続Dayの反復を防げない。却下
- 案B: memory_bufferに余韻を含める → メモリの目的と混同する。却下
- 案C（採用）: 直近3件の余韻をリスト蓄積 → トークン増加最小限で非連続Day反復も防止
