# Requirement — CSDG 厳密システムレビュー

## 背景

49 件の `.steering/` タスクのうち、直近 30 件 (2026-03-28 以降) の大半が「diary-quality」「critic-quality-improvement」「tune-prompt」「fix-overloaded-retry」「best-of-n-last-write-wins」など、**生成品質の継続改善 / バグ修正** に集中している。Memory には `feedback_prompt_tuning_limits.md` で「LLM 例文収束はプロンプト修正では根本解決不可、モグラ叩きになったら打ち止め」と記録されている。

これは、戦術的反復の限界に達している可能性がある。一歩引いて、CSDG のアーキテクチャ・コード・運用を **戦略レベルで厳密判定** する必要がある。

## ゴール

- [x] CSDG コードベースの広域マップ作成
- [x] Actor-Critic 3-Phase Pipeline / schemas / プロンプト管理 / Self-Healing の深い読解
- [x] テスト品質 (カバレッジ / E2E 比率 / モック設計) の観測
- [x] ランタイムログ (generation_log.json) からの実態抽出
- [x] Codex への architectural 第二意見の取得 (1-2 query)
- [x] CRITICAL / HIGH / MEDIUM / LOW で分類した厳密判定レポート生成

## 非ゴール

- 個別バグの修正 (本タスクは判定のみ、実装は別タスクへ送る)
- プロンプトの再チューニング (memory 記録通り、ここでは打ち止め判定の根拠を示す)
- 仕様変更の決定 (推奨を提示するに留める)

## 完了条件 (Definition of Done)

- [ ] `.steering/20260507-system-strict-review/strict-review.md` レポート生成
- [ ] レポート内で各判定に **コードや log の具体根拠** を引用
- [ ] 「もう一段の評価軸」(行動可能な提案) を最低 5 個提示
- [ ] CLAUDE.md の禁止事項に違反しない (schemas.py 破壊的変更を提案しない、ペルソナ禁則無視を勧めない 等)
