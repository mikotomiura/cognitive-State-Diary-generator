# 要件定義: ブログ品質チューニング（advice.md 準拠）

## 背景
選考課題の評価基準が「出力の面白さ」であることが判明。
現在の CSDG は技術基盤として十分だが、出力を「継続購読したいブログ」にするための品質改善が必要。

## 実装内容
advice.md の6タスクを判定・実装する:

1. System_Persona.md にブログ情報追加 → **有効**
2. Prompt_Generator.md の改修（ブログ化+面白さ+感情決壊統合） → **有効（既存ルールとの統合要）**
3. scenario.py のシナリオ全面改訂（伏線4本+感情決壊構造） → **有効**
4. Prompt_Critic.md に面白さ評価軸+感情決壊評価基準追加 → **有効（既存ルールとの統合要）**
5. critic.py の文字数チェック閾値を400文字ベースに更新 → **有効**
6. config.py パラメータ確認 → **有効（変更不要を確認済み）**

## 受け入れ条件
- [ ] 全プロンプト変更が glossary.md の用語と一致
- [ ] ペルソナの禁則事項が維持されている
- [ ] 既存テストが全Pass
- [ ] 新規テスト（文字数チェック）が追加されPass
- [ ] mypy strict / ruff 準拠

## 影響範囲
- prompts/System_Persona.md
- prompts/Prompt_Generator.md
- prompts/Prompt_Critic.md
- csdg/scenario.py
- csdg/engine/critic.py
- tests/test_critic.py
