# 要件定義: fix-memory-extract-keyerror

## バグの症状
Day 4-7 で `_llm_extract_beliefs_and_themes` が `KeyError: '\n  "new_beliefs"'` で失敗し、
長期記憶の LLM 抽出が全滅する。ルールベースフォールバックで動作は継続するが、
beliefs/themes が蓄積されず、プロンプトに注入される長期記憶コンテキストが空のまま。

## 期待される動作
`Prompt_MemoryExtract.md` の変数プレースホルダ (`{evicted_entries}` 等) のみ展開され、
JSON 例示の波括弧はリテラルとして残り、LLM に正しくプロンプトが送信される。

## 再現手順
1. `python3 -m csdg.main` を実行
2. Day 4 以降で memory_buffer が満杯になり eviction が発生
3. `_llm_extract_beliefs_and_themes` が呼ばれ `template.format()` で KeyError

## 影響範囲
- `csdg/engine/memory.py` の `_llm_extract_beliefs_and_themes`
- `prompts/Prompt_MemoryExtract.md`

## 受け入れ条件
- [ ] KeyError が発生しないこと
- [ ] テンプレート変数 (evicted_entries, current_beliefs, current_themes) が正しく展開されること
- [ ] JSON 例示がリテラルとして LLM に渡されること
- [ ] 既存テストが全て通ること
