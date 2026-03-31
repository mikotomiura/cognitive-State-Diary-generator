# 要件定義: Critic弁別力の構造的改善 (v3)

## 背景
L3(LLM Judge)が全Day 4/4/4を返すためfinal range=0。L1/L2の弁別力を最終スコアに反映する仕組みが必要。

## 実装内容
- Change A: L1/L2コンセンサス補正 (_compute_final_score)
- Change B: L1 emotional 5段階化 + ペナルティ
- Change C: 余韻trigram類似度チェック
- Change D: L3プロンプトへのL1/L2構造化注入

## 受け入れ条件
- [ ] Final score range >= 2
- [ ] L1 avg std > 0.3
- [ ] 余韻trigram検出が動作
- [ ] 全テストPass, mypy strict, ruff clean
