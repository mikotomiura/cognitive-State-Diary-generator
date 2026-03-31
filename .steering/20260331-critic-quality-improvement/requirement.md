# 要件定義: Critic品質改善 & 日記生成多様性向上

## 背景
Criticの弁別力がゼロ(L1/L2が常に5.0)であり、日記コンテンツに余韻テンプレート化・場面構造反復・哲学者引用違反が発生している。

## 実装内容
1. L1/L2を基本スコア3.5+加点方式に変更
2. 余韻テンプレート反復チェック追加
3. Critic重み調整
4. プロンプト改善(余韻/場面多様性)
5. 場面構造パターン追跡・注入
6. 哲学者引用カウンター実装
7. テスト更新
8. 検証スクリプト作成

## 受け入れ条件
- [ ] L1/L2スコアの標準偏差 > 0.3
- [ ] 最終スコアのレンジ >= 2
- [ ] 既存テスト全Pass
- [ ] mypy strict / ruff 準拠

## 影響範囲
- csdg/engine/critic.py
- csdg/engine/pipeline.py
- csdg/engine/actor.py
- csdg/config.py
- prompts/Prompt_Generator.md
- tests/test_critic.py
- tests/test_pipeline.py
