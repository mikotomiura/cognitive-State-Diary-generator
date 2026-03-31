# タスクリスト: 日記生成品質のプロンプトチューニング

## 実装タスク
- [x] P1: Prompt_Generator.md — 余韻禁止構文追加 + 多様な余韻例
- [x] P2: Prompt_Generator.md — 概念語頻度制限追加
- [x] P3: Prompt_Generator.md — 本文フレーズ重複防止強化
- [x] P4: Prompt_Generator.md — 高インパクト短文連打の必須化強化
- [x] P5: Prompt_Generator.md — 冒頭イメージ回収ルール追加
- [x] P3/P4/P5: Prompt_Critic.md — 評価基準追加

## 検証タスク
- [x] 問題のあったDay (1, 3, 4) を再生成して改善確認
- [x] 全Day再生成で他Dayへの悪影響なし確認 (0リトライ, 0フォールバック)
- [x] log-analyzerで全体品質再分析

## ドキュメント更新
- [x] .steering/decisions.md に変更前後のスコアを記録
