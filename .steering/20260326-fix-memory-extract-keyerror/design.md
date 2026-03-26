# 設計: fix-memory-extract-keyerror

## 根本原因
`Prompt_MemoryExtract.md` の37-40行目に JSON 例示がある:
```
{
  "new_beliefs": ["追加すべき信念のリスト"],
  "new_themes": ["追加すべきテーマのリスト"]
}
```
Python の `str.format()` がこれらの `{` `}` をフォーマット変数として解釈し、
`'\n  "new_beliefs"'` という名前の変数を探して KeyError になる。

## 修正アプローチ
`Prompt_MemoryExtract.md` の JSON 例示内の波括弧を `{{` `}}` にエスケープする。
`str.format()` は `{{` を `{` リテラルとして出力する。

## 変更対象ファイル
| ファイル | 変更内容 |
|---|---|
| `prompts/Prompt_MemoryExtract.md` | JSON 例示の `{` `}` を `{{` `}}` にエスケープ |

## 代替案と選定理由
- memory.py 側で `str.format()` → `str.replace()` に変更する案
  → プロンプトテンプレート側の修正の方がシンプルで、コード変更が不要
