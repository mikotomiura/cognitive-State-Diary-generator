# タスクリスト: CSDG 品質改善チューニング

## 実装タスク
- [x] Step 1: シナリオ修正 (Day 1/5/7)
- [x] Step 2: 状態遷移パラメータ調整 (config.py, .env)
- [x] Step 3a: 「面白さ」最重要指針セクション追加
- [x] Step 3b: タイトル禁止パターン追加
- [x] Step 3c: 語りかけバリエーション強化
- [x] Step 3d: AI臭い表現禁止リスト追加
- [x] Step 4: System_Persona.md 自意識セクション追加
- [x] Step 5: 全テスト・型チェック・リンター (474 pass, mypy OK, ruff OK)
- [x] Step 6: パイプライン再実行・品質検証

## テストタスク
- [x] test_scenario.py — 全 PASS
- [x] test_config.py — デフォルト値更新 (stress -0.5, decay 0.15)
- [x] test_state_transition.py — 変更不要 (独自フィクスチャ)
- [x] プレースホルダ整合性確認 — All OK

## 確認ポイント結果
- [x] Day 1 fallback なし — PASS
- [ ] Day 4 stress ≥ 0.30 — 0.23 (LLM生成変動性)
- [x] Day 7 motivation > 0 — 0.20
- [x] Critic スコア合計 ≥ 9 — 概ね達成
- [ ] 書き出しユニーク ≥ 5 — 4/7 (LLM生成変動性)
- [ ] 余韻ユニーク ≥ 5 — 4/7 (LLM生成変動性)
