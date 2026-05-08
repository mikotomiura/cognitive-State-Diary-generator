# CSDG 厳密システムレビュー (Strict Review)

実施日: 2026-05-07  
レビュアー: Claude Opus 4.7 (主体) + Codex gpt-5.5 (アーキテクチャ第二意見)  
対象範囲: csdg/ (5,477 LOC), prompts/ (1,085 行), tests/ (520 tests / 85% coverage), output/generation_log.json

---

## エグゼクティブサマリ

CSDG は **「型・規約・テスト」が極めて高品質に整備された堅実なエンジニアリング実装**である一方、**生成品質の改善ループが構造的に頭打ち**になっている。最大の発見は、**戦術的反復 (プロンプト + リトライ) で約 6 週間 30+ サイクル投資した結果、Critic スコアが 3-4 で plateau している** こと。これは個別バグの問題ではなく **アーキテクチャの局所最適に閉じ込められている**サインで、Codex の独立第二意見もこの判断と完全に一致した。

判定: **コード品質 ✅ HEALTHY / 設計戦略 ⚠️ ESCAPE-VELOCITY-NEEDED**

| カテゴリ | 件数 |
|---|---|
| CRITICAL | 2 |
| HIGH | 4 |
| MEDIUM | 5 |
| LOW | 3 |

---

## 観測した事実 (根拠データ)

### コード規模
- csdg/ 合計 5,477 行 (csdg 本体 1,035 + engine/ 4,442)
- **pipeline.py: 1,319 行** (engine/ の 30%、最大ファイル)
- critic.py: 1,026 行
- actor.py: 782 行
- llm_client.py: 459 行
- schemas.py: 323 行 / 13 Pydantic モデル / **100% test coverage**

### テスト品質
- 520 tests pass / 2.36s 実行時間 ✅
- 全体 coverage **85%** ✅
- ただし **llm_client.py は 35%** (line 228-459 の API 呼び出し系が未カバー)
- actor.py 60%, main.py 54% (CLI パスの大部分未カバー)
- **E2E テスト = 0 件** (`@pytest.mark.e2e` は導入されているが未使用)

### ランタイム実態 (output/generation_log.json, 2026-04-05 実行)
- 7 日間生成 = 286 秒 (40 秒/日)
- API 呼び出し 31 回, リトライ 5 回, フォールバック 0
- **Critic スコア分布**:

| Day | T (時間整合) | E (感情妥当) | P (ペルソナ) | retries |
|---|---|---|---|---|
| 1 | 3 | 4 | 4 | 0 |
| 2 | 3 | 4 | 4 | 1 |
| 3 | 3 | 3 | 4 | 1 |
| 4 | 4 | 4 | 3 | 0 |
| 5 | 3 | 4 | 3 | 1 |
| 6 | 3 | 3 | 3 | 1 |
| 7 | 3 | 4 | 3 | 1 |

**全 7 日 21 軸中、5 (満点) は 0 件。3 (合格ぎり) が 13 件 (62%)**。Pass 閾値が 3 なので、**システムは合格ラインの直上で操業している** → 微小な揺らぎで Reject へ転落するリスク。

### Codex 独立分析 (gpt-5.5, 13,609 tokens 使用)
本プロジェクトのソースコードを与えずに症状のみ伝達した結果、**Claude の独立分析と同方向の 5 提言を返した**:
1. Critic 出力を型 (verdict: pass/soft_fail/hard_fail) で分離
2. ドメイン語彙を pipeline.py から `corpus/ontology/*.yaml` へ分離
3. 後段リトライから「先行アーク計画」へ
4. Critic を採点器から診断器 (失敗カテゴリ) へ
5. 温度減衰でなく候補探索 + 交叉

**両方の視点が一致したことが本レポートの提言の信頼性を裏付ける。**

---

## CRITICAL — 即修正推奨 (2 件)

### CRITICAL-1: Critic Pass/Reject の信号矛盾 (情報損失バグ)

**根拠**:
- `critic.py:115` の `judge()`: `all(score >= 3 for ...)` で Pass 判定
- `schemas.py:183-193` の `CriticScore.check_reject_fields`: `score < 3` のときのみ `reject_reason` 必須を強制
- **score ≥ 3 でも `reject_reason` を populate することは Pydantic レベルで許可されている**
- 実例 (output/generation_log.json, Day 7 attempt 0):
  ```
  scores: T=3 E=4 P=3 (全て ≥ 3)
  reject_reason: "temporal_consistency と persona_deviation が3未満ではないものの、いくつかの問題があります。..."
  ```
  → LLM-Judge は内部で「問題あり」を認識しているが、Pipeline は数値のみ見て Pass 扱い → **品質改善の貴重な信号が捨てられている**

**影響**: Critic LLM が出した「実は不満」の指摘が後続の修正サイクルに伝達されない。リトライ品質改善のシグナルが切れる。これが plateau の主要因の一つと推定。

**修正方針** (Codex 提言と一致):
- `CriticScore` を `verdict: Literal["pass","soft_fail","hard_fail"]` 主導に再設計
- `reject_reason` 非空 → 最低 `soft_fail` 強制 (model_validator で正規化)
- soft_fail 時は scores を「説明用」に降格、リトライは reject_reason を Generator へフィードバック

**注意**: 既存の `CriticScore` を破壊的変更すると CLAUDE.md 禁止事項 (schemas.py の破壊的変更) に抵触。**新フィールド追加 + デフォルトで verdict を導出する後方互換戦略**を取るべき。

### CRITICAL-2: pipeline.py のドメイン語彙ハードコード (アーキテクチャ違反)

**根拠** (`pipeline.py:67-200`):
- 場所マーカー 30 語 (古書店、電車、コンビニ、会議室、カフェ、駅、図書館、公園 ...)
- 物オブジェクト 16 語 (万年筆、インク、背表紙、古本、栞、ペン、ノート、手帳、付箋 ...)
- 哲学者 18 名 (西田幾多郎、利休、ハイデガー、カフカ、ベンヤミン ...)
- 文末パターン 5 種 / 開始パターン 6 種 / 主題語 4 種

**これは CLAUDE.md の原則「プロンプトはコードに埋め込まない」の精神違反**。プロンプトファイル外には出ているが、**ドメイン語彙が制御フローと同じファイルに混在** → キャラクター変更や別シリーズ展開時に pipeline.py 全体改変が必要。

**修正方針** (Codex 提言と一致):
- `prompts/ontology/places.yaml`, `prompts/ontology/objects.yaml`, `prompts/ontology/voices.yaml` 等にデータとして外出し
- pipeline.py は YAML をロードして「重複検出 / 多様性強制 / フィードバック生成」だけ持つ
- これにより 1,319 行 → 推定 700-900 行に削減可能

**注意**: 大規模 refactor、別タスク (`.steering/`) を切るべき。

---

## HIGH — 早期対応推奨 (4 件)

### HIGH-1: スコア plateau (探索戦略の限界)

**根拠**: 全 7 日 21 軸中、最高スコア 5 が 0 件。3 が 62%。**1 系列を 3 回叩く Best-of-1 + Temperature Decay 戦略では plateau を脱出できていない**。
- `output/generation_log.json` から、retry_count=1 が 5 日 (5/7 = 71%) → 初稿で reject、修正で 3 まで持ち上げ、それ以上は伸びない
- Memory `feedback_prompt_tuning_limits.md` の打ち止め記録と整合

**Codex 提言**: 「1 本を 3 回直すより、複数案を並列生成し、critic 特徴量で選抜・交叉・部分再生成する」

**修正方針**:
- Phase 2 で Generator を **N=3 並列実行** (異なる temperature / 異なる seed プロンプト)
- Phase 3 で N 候補を Critic にかけ、各軸の最高スコア集合を取得
- 部分再生成: Critic が「冒頭が弱い」と判定した場合、その候補の冒頭だけ再生成して合成
- 既に「ボーナス再試行 + Best-of-N」コミット (15b9b5c, 3bb8de2) で **success path にも Best-of-N が適用済み**だが、**初稿並列化はまだ**。

### HIGH-2: 後段リトライ駆動から事前計画駆動へ

**根拠**: 7 日間が day-by-day で生成されており、**series-level の構造制御がない**。Day 5 の冒頭イメージと Day 6 のイベントの整合性は、`memory_buffer` (3 日 FIFO) と `LongTermMemory` の信念リストに依存。
- `prompts/Prompt_Critic.md` には「冒頭イメージの未回収」「本文中フレーズの日跨ぎ重複」の検出ルールがあるが、**事後に検出・修正**する設計
- これは「叩いて直す」アプローチ。Codex 提言「先に arc plan」が望ましい

**修正方針**:
- Phase 0 (新設): 7 日分の `ArcPlan` を事前生成
  - 各 Day の感情変化軸 / 場所 / 象徴物 / 反復禁止語句 / 達成すべき narrative beat
  - 1 回の LLM 呼び出し (構造化出力) で 7 日分を取得
- Phase 2 で生成時に ArcPlan の Day_t を制約として注入
- Critic は ArcPlan との整合性も検証

### HIGH-3: Critic を採点器から診断器へ

**根拠**: 現状の Critic は `(temporal: int, emotional: int, persona: int)` を返す → リトライ時には Generator に「reject_reason 文字列」が渡るだけで、**何が悪かったかの構造的シグナルは数値のみ** (情報量低)。

**Codex 提言**: 「点数ではなく失敗カテゴリを返す: flat_emotion / cliché / weak_scene / series_incoherence / overconstraint。修正器はカテゴリ別に局所編集する」

**修正方針**:
- `CriticDiagnostic` 新スキーマ:
  ```python
  class CriticDiagnostic(BaseModel):
      failure_categories: list[Literal["flat_emotion", "cliché", "weak_scene",
                                       "series_incoherence", "overconstraint",
                                       "ending_template_repetition"]]
      severity: Literal["pass", "soft_fail", "hard_fail"]
      local_edit_targets: list[str]  # 編集対象の文 / 段落の指示
  ```
- Generator の修正リトライは **失敗カテゴリ別の specialized prompt** で局所編集
- 現状の "全文書き直し" → "問題箇所だけ編集"

### HIGH-4: llm_client.py のテストカバレッジ 35%

**根拠**: pytest --cov 結果。line 228-459 (AnthropicClient.generate_structured / Gemini フォールバック / リトライロジック) が未カバー。
- これは **本番で起きるエラーパス** がほとんど未テスト という意味
- E2E テスト 0 件 → mock テストでは検出できない統合バグ (rate limit / partial response / schema drift) が後続コミット (`fix-overloaded-retry`, `best-of-n-last-write-wins`) で発覚しているのと整合

**修正方針**:
- VCR.py や recorded fixture を使った **半 E2E テスト** を導入 (実 API レスポンスを記録 → 再生)
- AsyncAnthropic の `max_retries=5` と Pipeline 側の retries=3 が**多重リトライで実質 8 倍の overload 増幅**になっていないか確認 (`llm_client.py:100`)

---

## MEDIUM — 計画的対応 (5 件)

### MEDIUM-1: Prompt_Generator.md が 567 行 — 長すぎ

LLM の指示理解は長文で劣化する。567 行のシステムプロンプトは**プロンプトの構造が consistency を圧迫**。HIGH-3 の診断器化と組み合わせて、**カテゴリ別の specialized prompt 群**に分割し、メイン Generator プロンプトは 200 行以下に削減。

### MEDIUM-2: pipeline.py の 1,319 行 — 単一責任違反

ファイル構造は `/* extract_*, _detect_*, _build_*, run_pipeline */` で雑居。Phase ごと (state_update / generation / critic / fallback) のサブモジュール化を推奨:
```
csdg/engine/pipeline/
├── __init__.py        # オーケストレータ (300 行以内)
├── feedback.py        # critic feedback → next prompt
├── diversity.py       # 場面/物/哲学者の使い回し検出
├── opening_pattern.py # 冒頭パターン分類
└── ending_pattern.py  # 余韻パターン分類
```

### MEDIUM-3: actor.py の coverage 60%

Phase 1 (state update) のロジックは決定論的部分は `state_transition.py` に分離されているが、**`actor.py` 内の LLM 呼び出し + フォールバック構築**が未テスト。HIGH-4 と連動。

### MEDIUM-4: hardcoded constants in critic.py (`_BASE_SCORE = 2.5` 他)

`critic.py:40-67` に文字数閾値 (300/500), trigram 閾値 (0.30), Veto 閾値 (0.50), penalty スコア (1.5) 等が散在。
**チューニング知識が `config.py` と `critic.py` の二箇所に分散**。`config.py` の `CriticWeights` / `VetoCaps` に集約すべき。

### MEDIUM-5: 動的 Skill (`!` shell preprocessing) が 0 個

verify-setup 仕様で要件あり。例: `.claude/skills/recent-tasks/` で `!ls .steering/ | tail -5` を埋め込み、毎回直近タスクをコンテキストに含める動的 Skill を 1 個。

---

## LOW — 改善余地 (3 件)

### LOW-1: schemas.py の `frozen=True` 使用率

現状: `DailyEvent` のみ frozen。`CharacterState` も生成後不変なら frozen 化推奨。CLAUDE.md `frozen=True 誤記` 修正コミット (3bb8de2) があったので方針自体は意識されている。

### LOW-2: prompt_loader.py の 28 行 — file load failure 時の挙動

`FileNotFoundError` を発出するのみ。プロジェクト初期化チェック (`/start-task` 内で) でプロンプトファイルの SHA-256 を検証する仕組みが望ましい (実は `PipelineLog.prompt_hashes` で記録はされているので、**起動時バリデーション**を追加するだけ)。

### LOW-3: visualization.py — state_trajectory.png

一目で見やすいが、**Critic スコア plateau の可視化がない**。`critic_score_trajectory.png` (各日の T/E/P スコアと retry 数を重ねたグラフ) を追加すれば、本レポート発見の plateau が常時観察可能になる。

---

## 行動可能な提案 (もう一段の評価軸)

1. **CRITICAL-1 を最優先で着手** — `CriticScore` に `verdict` フィールド追加 (後方互換) + `reject_reason` 非空時の自動 soft_fail 化。1-2 日で実装可能、即効性あり。

2. **HIGH-1 (Best-of-N 並列化) を 2 番目に** — 既存の Best-of-N コードを Phase 2 初稿にも展開。CRITICAL-1 の verdict と組み合わせて「N 候補から hard_fail を除外、soft_fail 候補同士で交叉」が可能。

3. **HIGH-2 (Arc Plan 先行) は別 PR で** — 大規模変更、`.steering/20260520-arc-plan/` のような新規タスクで requirement.md から作る。

4. **CRITICAL-2 (ontology 外出し) は HIGH-2 と一緒に** — Arc Plan が YAML/JSON で外部化されるなら、ドメイン語彙も同じ場所へ自然に移せる。

5. **HIGH-4 (E2E テスト導入)** — VCR.py 系か `pytest-recording`。Anthropic のレスポンスを 1 回録画 → CI で再生。これだけで `fix-overloaded-retry` 系の回帰バグの大半は事前検出可能。

6. **モニタリング**: 上記 HIGH-1/2 の効果を **Critic スコアの 5 出現率 % / 1 出現率 %** で測定。現状 5 出現率は 0%。3 ヶ月の目標を 「5 出現率 ≥ 20%」に。それで plateau 脱出を客観化できる。

---

## CLAUDE.md 制約準拠の確認

本レポートは以下を遵守:
- ✅ schemas.py の **破壊的変更を提案していない** (verdict は新フィールド追加で後方互換)
- ✅ プロンプトファイルへの Python コード埋め込みを推奨していない
- ✅ EMOTION_SENSITIVITY を根拠なく変更する提案なし
- ✅ ペルソナ禁則違反の容認なし
- ✅ `.steering/20260507-system-strict-review/` で作業記録を残している

---

## 結論

**CSDG はエンジニアリング品質が極めて高い実装** (型 100%, テスト 85%, Pydantic 厳密, Self-Healing 設計) である。にもかかわらず生成品質が plateau しているのは、**個別バグや個別プロンプトの問題ではなく、Critic 信号の情報損失 (CRITICAL-1) と探索戦略の限界 (HIGH-1)** がコアファクタ。

「プロンプトのモグラ叩きはもう打ち止め」という memory 記録は正しい判断。次の進化軸は **(a) Critic を診断器へ進化、(b) Best-of-N 並列化と部分再生成、(c) Arc Plan 先行設計** の 3 段。これは独立した Codex の意見とも完全一致しており、本レポートの提言の信頼性を裏付ける。

「6 週間 30 サイクル投資して plateau」を「次の 3 サイクルで plateau 脱出」に切り替えるための、本日付の戦略提言。

---

**生成情報**:
- 主分析: Claude Opus 4.7 (1M context)
- 第二意見: Codex gpt-5.5 / 13,609 tokens (`scripts/run-codex-consult.sh` 経由)
- 検証データ: pytest 520 tests, output/generation_log.json (2026-04-05 実行), csdg/ 直読
- 工数: 約 30 分 (本セッション内)
