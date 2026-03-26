# 要件定義: プロンプトチューニング

## 背景
日記品質分析（reserch.md）の結果、10件の問題（P0×3, P1×4, P2×3）が特定された。
advice.md の Phase A〜E に従い、プロンプト修正・検証を行う。

## 実装内容
3つのプロンプトファイルに対する6件の修正適用と効果検証

## 受け入れ条件
- [ ] 修正1〜6 の適用完了
- [ ] テスト全パス
- [ ] パイプライン再実行（7Day完走）
- [ ] 品質指標チェック通過

## 影響範囲
- prompts/Prompt_Generator.md — 修正1,2,3,5
- prompts/Prompt_Critic.md — 修正4
- prompts/System_Persona.md — 修正6
