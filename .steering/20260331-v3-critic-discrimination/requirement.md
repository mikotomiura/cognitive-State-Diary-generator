# 要件定義: v3 Critic 弁別力改善

## 背景
v2 の Critic は L3 (LLMJudge) が全 Day で同一スコア (4/4/4) を返し、
`_BASE_SCORE=3.5` + weights `0.35/0.30/0.35` の組み合わせで
最終スコアが全て 4 に収束する構造的ボトルネックがある (final range = 0)。

## 実装内容
1. `_BASE_SCORE` を 3.5 → 2.5 に変更 (L1/L2 の弁別レンジ拡大)
2. Critic 重みを 0.40/0.35/0.25 に変更 (L3 アンカー効果の低減)
3. Prompt_Generator.md の余韻セクションを構造化手順に置換
4. テスト期待値の修正
5. 検証スクリプトに加重平均 range 判定を追加

## 受け入れ条件
- [ ] L3=4.0 固定でも final range >= 2 が数学的に保証される
- [ ] pytest 全テスト pass
- [ ] mypy strict / ruff 準拠
- [ ] v2 で確認済みの加点・減点ロジックは一切変更なし

## 影響範囲
- csdg/engine/critic.py (_BASE_SCORE 定数のみ)
- csdg/config.py (CriticWeights, CSDGConfig のデフォルト値)
- prompts/Prompt_Generator.md (余韻セクション)
- tests/test_critic.py, tests/test_config.py (期待値)
- scripts/verify_critic_discrimination.py (加重平均 range 判定追加)
