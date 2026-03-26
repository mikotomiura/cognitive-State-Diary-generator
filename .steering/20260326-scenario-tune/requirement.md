# 要件定義: シナリオチューニング (advice.md 改善案)

## 背景
advice.md に記載された3つの改善案を、generation_log.json の実データで検証した結果、
すべて有効と判断した。

## 実データからの裏付け
- Day 5: Critic 5/5/5 で deviation 極小だが、Day 4 (impact=-0.9) → Day 5 (impact=+0.4) の回復速度は物語的に不自然
- Day 1: temporal_consistency=4 (全Day中最低タイ)。memory_buffer 空のため評価基盤が弱い
- 那由他: relationships 値が7日間不変 (0.6 固定)。更新ロジック未検証

## 実装内容
1. Day 5 の emotional_impact を 0.4 → 0.15 に下げ、description を「傷が癒えない中の小さな気づき」に調整
2. Day 1 の description に Day 3 (コードレビュー否定) ・Day 4 (AI自動化) への伏線を追加
3. Day 6 に那由他との交流要素を含め、domain を「人間関係・内省」に変更

## 受け入れ条件
- [ ] scenario.py の DailyEvent が Pydantic バリデーションを通過する
- [ ] 既存テスト (test_scenario.py 等) が全て通る
- [ ] Day 5 の impact が 0.15、event_type が "neutral" のまま
- [ ] Day 1 の description に仕事への違和感の種が含まれる
- [ ] Day 6 の description に那由他との交流が含まれる
- [ ] relationships に那由他が既に存在する (INITIAL_STATE で 0.6)

## 影響範囲
- `csdg/scenario.py` のみ（プロンプト・コードロジックの変更なし）
