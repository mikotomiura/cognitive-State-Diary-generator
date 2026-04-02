# 要件定義: CSDG 品質改善チューニング

## 背景
advice.md に記載された品質改善案6ステップを実装する。
emotional_impact と event_type の矛盾修正、状態遷移パラメータ調整、プロンプト品質向上を行う。

## 実装内容
1. シナリオ修正 (Day 1/5/7 の impact・event_type・description)
2. 状態遷移パラメータ調整 (.env + config.py)
3. Prompt_Generator.md の改善 (面白さ指針・タイトル禁止・語りかけ・AI臭禁止)
4. System_Persona.md の微調整 (ブログ記事としての自意識)
5. テスト実行・型チェック・リンター
6. パイプライン再実行・品質検証

## 受け入れ条件
- [ ] Day 1 が fallback なしで Pass
- [ ] Day 4 の stress が 0.30 以上
- [ ] Day 7 の motivation > 0
- [ ] 全テスト通過
- [ ] プレースホルダ整合性確認

## 影響範囲
- csdg/scenario.py
- csdg/config.py
- .env
- prompts/Prompt_Generator.md
- prompts/System_Persona.md
- tests/test_config.py
