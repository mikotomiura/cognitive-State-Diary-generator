# 要件定義: Critic品質改善 v2 (検証結果に基づく追加修正)

## 背景
v1修正後の検証で L1/L2 平均std < 0.3、最終スコアrange = 1 と未達。
データ分析に基づき3つの有効な追加修正を実施する。

## 実装内容
1. L1 emotional: deviation閾値を3段階に細分化 (0.03/0.08/0.15)
2. L2 temporal: punct_ratioを0.070-0.080に狭窄 + 文数30-50ボーナス追加
3. pipeline: 場面構造パターン検出順序を 古書店型→会議型→帰路型 に変更

## 受け入れ条件
- [ ] L1 平均std > 0.3
- [ ] L2 平均std > 0.3
- [ ] 最終スコア overall range >= 2
- [ ] 帰路型 <= 2/7
- [ ] 全テストPass, mypy strict, ruff clean
