# 設計: プロンプトチューニング

## 実装アプローチ

advice.md の6件の修正案を検証し、有効と判定されたものを3つのプロンプトファイルに適用する。

### 変更の方針
- プロンプトテキストの追加・置換のみ。コード変更なし。
- 新しいプレースホルダ `{...}` は追加しない（`template.format()` の互換性維持）
- glossary.md のユビキタス言語に準拠した用語を使用

## 変更対象ファイル

| ファイル | 変更内容 | 対応する問題ID |
|---|---|---|
| prompts/Prompt_Generator.md | 書き出しバリエーション指示の追加 | P0-1 |
| prompts/Prompt_Generator.md | 感情爆発時の文体指示の具体化（セクション置換） | P1-1 |
| prompts/Prompt_Generator.md | 古今接続と比喩素材の多様性指示（新規セクション） | P1-2, P1-3 |
| prompts/Prompt_Generator.md | 表現の多様性に関する注意事項（新規セクション） | P2-1, P2-2, P2-3 |
| prompts/Prompt_Critic.md | temporal_consistency の重点的な検出ポイント追加 | P0-2, P1-4 |
| prompts/System_Persona.md | 属性テーブルに「現在の年 2026年」を追加 | P0-3 |

## 代替案と選定理由

### 代替案1: 1件ずつ適用・検証（tune-prompt の鉄則）
- メリット: 効果の個別測定が可能
- デメリット: パイプライン再実行7回必要（各回約5分 × 7 = 35分）
- 却下理由: advice.md が一括適用を指示。修正案間に依存関係がなく、プレースホルダ衝突リスクもないため一括適用を採用

### 代替案2: Prompt_Generator.md のみ修正
- メリット: 影響範囲が1ファイルに限定
- デメリット: temporal_consistency の検出強化（Critic側）と年代明示（Persona側）が漏れる
- 却下理由: P0-2, P0-3 は Critic / Persona 側の修正が必要

## 安全性の検証

impact-analyzer サブエージェントにより以下を確認済み:
- Prompt_Generator.md: `template.format()` のプレースホルダ4つ（current_state, event, memory_buffer, revision_instruction）のみ。新規 `{...}` の混入なし
- Prompt_Critic.md: `template.format()` のプレースホルダ5つのみ。新規 `{...}` の混入なし
- System_Persona.md: `format()` 呼び出しなし。任意のテキスト追加が安全
