# CSDG 改善計画 — 次セッションへの引き継ぎ

作成日: 2026-05-07  
作成者: Claude Opus 4.7 (1M context) + Codex gpt-5.5 (architectural 第二意見)  
基礎レポート: `.steering/20260507-system-strict-review/strict-review.md`

---

## 0. 次セッションへの引き継ぎ要項

このファイルは **本セッションのコンテキストを引き継がない新セッション** が、自己完結的に作業を再開できるように書かれている。

### 新セッションで最初にやること

1. **このファイル全文を Read** で読む
2. `.steering/20260507-system-strict-review/strict-review.md` も Read で読む (詳細根拠)
3. 着手する Sprint をユーザーに確認 (下記「実行ロードマップ」参照)
4. 該当 Sprint ごとに **新 `.steering/[YYYYMMDD]-<task>/`** を `/start-task` で立てる (本ファイルの Sprint 単位 = 新タスク 1 件 を原則)
5. requirement.md に「親レポート: `.steering/20260507-system-strict-review/`」を必ず引用

### 重要原則 (CLAUDE.md 制約の再掲)

- ❌ schemas.py の **破壊的変更禁止**: 既存テストを壊す削除/型変更をしない (新フィールド追加 + デフォルト値で後方互換)
- ❌ プロンプトに Python コード埋め込み禁止
- ❌ EMOTION_SENSITIVITY を**根拠なく**変更しない
- ❌ ペルソナ禁則違反を容認しない
- ✅ 各タスクで .steering 作業記録必須
- ✅ レビュー系 agent (code-reviewer / test-analyzer / security-checker) は opus
- ✅ 重要 PR は `/cross-review` で Codex 第二意見

---

## 1. 改善計画の 3 ストリーム

| ストリーム | 内容 | コア課題 | 規模 |
|---|---|---|---|
| **A. Architecture (戦術)** | Critic / Best-of-N / Arc Plan | スコア plateau 脱出 | 中-大 |
| **B. Persona Engine Pivot (戦略)** | engine 分離 + surfaces + 軽量 world | 独自貢献の engine 化 | 大 |
| **C. OSS Hygiene** | LICENSE + SECURITY + CI 等 | 公開リポジトリの法的整備 | 小-中 |

A は plateau 脱出の即効性、B は中期的価値、C は並行作業可能。

---

## 2. 実行ロードマップ (推奨順)

```
Sprint 1 (1-2 日)   : C-Phase1 (LICENSE 等 CRITICAL OSS)        ← 並行で進めやすい
Sprint 2 (1-2 週)   : A-CRITICAL-1 + A-HIGH-1                   ← plateau 脱出の核
Sprint 3 (1 週)     : C-Phase2 (SECURITY/CONTRIBUTING/CI)
Sprint 4 (2-4 週)   : A-HIGH-2 + A-HIGH-3 + B-Phase1 (engine 分離 refactor)
Sprint 5 (1-2 週)   : A-HIGH-4 (E2E test) + A-MEDIUM 群
Sprint 6+ (任意)    : B-Phase2 (surfaces 追加) + B-Phase3 (軽量 world)
```

並行可: Sprint 1 と Sprint 2 は別タスクで同時着手可能。Sprint 3 と Sprint 2 後半も並行可。

---

## 3. ストリーム A: Architecture (戦術改善)

### A-CRITICAL-1: Critic verdict 導入 + reject_reason 矛盾解消

**根拠**: `critic.py:115` の `judge()` は `all(score >= 3)` で Pass 判定。`schemas.py:183` の `model_validator` は `score < 3` 時のみ `reject_reason` 必須。**score ≥ 3 でも reject_reason populate を許容** → 実例 (output/generation_log.json Day 7 attempt 0) で score=3,4,3 全合格でも reject_reason に「いくつかの問題」が記録、しかし Pipeline は数値のみ見て Pass 扱い → **品質改善信号の情報損失**。

**実装方針** (CLAUDE.md 制約遵守):
1. `csdg/schemas.py` の `CriticScore` に **新フィールド追加** (破壊的変更禁止):
   ```python
   class CriticScore(BaseModel):
       # 既存フィールド (変更なし)
       temporal_consistency: int
       emotional_plausibility: int
       persona_deviation: int
       hook_strength: float = 0.0
       reject_reason: str | None = None
       revision_instruction: str | None = None
       # 新規追加 (デフォルト値で後方互換)
       verdict: Literal["pass", "soft_fail", "hard_fail"] = "pass"

       @model_validator(mode="after")
       def derive_verdict(self) -> CriticScore:
           # 既存の check_reject_fields 実装を保持しつつ verdict を自動導出
           min_score = min(self.temporal_consistency, self.emotional_plausibility, self.persona_deviation)
           if min_score < 3:
               self.verdict = "hard_fail"
           elif self.reject_reason:  # score >= 3 でも reject_reason あり → soft_fail
               self.verdict = "soft_fail"
           else:
               self.verdict = "pass"
           return self
   ```
2. `csdg/engine/critic.py:115` の `judge()` を verdict 主導に書き換え:
   ```python
   def judge(score: CriticScore) -> bool:
       return score.verdict == "pass"  # soft_fail / hard_fail はリトライ対象
   ```
3. `csdg/engine/pipeline.py` のリトライループで `verdict` を見て、soft_fail 時は `reject_reason` を Generator のフィードバックに含める

**触るファイル**: `csdg/schemas.py`, `csdg/engine/critic.py`, `csdg/engine/pipeline.py`, `tests/test_schemas.py`, `tests/test_critic.py`, `tests/test_pipeline.py`

**完了条件**:
- [ ] 既存の 520 tests がすべて緑のまま
- [ ] verdict フィールドのテスト追加 (pass / soft_fail / hard_fail 各ケース)
- [ ] Day 7 attempt 0 のような score=3 + reject_reason ケースで `verdict == "soft_fail"` が出ることを確認するテスト
- [ ] mypy --strict / ruff check 通過
- [ ] CHANGELOG / 該当 docs (architecture.md §3.3) を更新

**工数**: 1-2 日

**risk**: `model_validator` の order 依存に注意。既存 `check_reject_fields` と新 `derive_verdict` の順序を Pydantic v2 で確認。

---

### A-HIGH-1: Phase 2 初稿 Best-of-N 並列化

**根拠**: 全 7 日 21 軸中、最高スコア 5 は **0 件**。3 が 62%。1 系列 3 リトライ + Temperature Decay では plateau 脱出不可 (Codex 提言: 「1 本を 3 回直すより、複数案を並列生成し、critic 特徴量で選抜・交叉・部分再生成する」)。既存の Best-of-N は **ボーナス再試行成功 path にのみ適用** (commit 15b9b5c)。**初稿並列化はまだ**。

**実装方針**:
1. `csdg/engine/pipeline.py` の Phase 2 を `asyncio.gather()` で N=3 並列実行
2. 各候補で **異なる temperature** (0.7, 0.85, 0.55) または **異なる seed prompt 補正** (例: 「比喩型重視」「五感型重視」「断片型重視」)
3. N 候補を Critic にかけ、各軸の最高スコア集合 + verdict=pass の候補を採用
4. verdict=soft_fail 候補同士で「冒頭 / 中段 / 末尾」の最良パーツを合成 (Phase 4 で本格化)

**触るファイル**: `csdg/engine/pipeline.py`, `csdg/engine/actor.py`, `csdg/config.py` (`bestofn_count` パラメータ追加), `tests/test_pipeline.py`

**完了条件**:
- [ ] N=3 並列で API 呼び出しが正しく実行 (mock テスト)
- [ ] 1 候補が hard_fail でも他候補で pass があれば採用
- [ ] config の `bestofn_count=1` でデフォルト動作 (後方互換)
- [ ] 観測データ: スコア 5 の出現率を generation_log.json から計測

**工数**: 1 週間

**KPI**: 30 日後に「スコア 5 出現率 0% → 10%以上」を目標

---

### A-HIGH-2: Arc Plan (Phase 0) の導入

**根拠**: 7 日間が day-by-day 生成、series-level 構造制御がない (memory_buffer 3 日 FIFO のみ)。Codex 提言: 「7 日分を先に arc plan 化し、日ごとの感情変化・場所・象徴物・反復禁止を決めてから本文生成する」。

**実装方針**:
1. **新 Phase 0** を追加: 7 日分の `ArcPlan` を 1 回の構造化 LLM 呼び出しで取得
2. 新スキーマ (csdg/schemas.py に追加):
   ```python
   class DayArc(BaseModel):
       day: int
       emotional_axis: str  # "決壊→再起", "停滞", "気づき" 等
       primary_location: str  # "古書店", "会議室"
       symbolic_object: str  # "万年筆", "缶コーヒー"
       narrative_beat: str  # "問いが立つ", "回答を保留", "矛盾を抱える"
       forbidden_words: list[str]  # 反復禁止 (前日との重複)

   class ArcPlan(BaseModel):
       days: list[DayArc]  # length=7
       overarching_theme: str
       turning_point_day: int
   ```
3. `prompts/Prompt_ArcPlan.md` を新設 (200 行以下)
4. Phase 2 で生成時に DayArc を制約として注入
5. Phase 3 Critic は ArcPlan との整合性も検証

**触るファイル**: `csdg/schemas.py`, `csdg/engine/pipeline.py`, `prompts/Prompt_ArcPlan.md` (新規), `csdg/main.py`, `tests/`

**完了条件**:
- [ ] ArcPlan 生成 → 7 日生成の連動が動作
- [ ] ArcPlan を skip するモード (config flag) で旧動作も維持
- [ ] Critic が ArcPlan 違反を検出 (例: forbidden_words の使用) → soft_fail
- [ ] docs/architecture.md に Phase 0 を追加

**工数**: 2-3 週間

**依存**: A-CRITICAL-1 完了 (verdict 駆動が前提)

---

### A-HIGH-3: Critic を採点器 → 診断器へ

**根拠**: 現状の Critic は `(temporal: int, emotional: int, persona: int)` を返す → Generator への修正情報量が低い。Codex 提言: 「点数ではなく失敗カテゴリを返す: flat_emotion / cliché / weak_scene / series_incoherence / overconstraint」。

**実装方針**:
1. 新スキーマ:
   ```python
   class CriticDiagnostic(BaseModel):
       failure_categories: list[Literal[
           "flat_emotion", "cliché", "weak_scene", "series_incoherence",
           "overconstraint", "ending_template_repetition", "opening_unrecovered",
           "philosopher_namedrop", "voice_drift"
       ]]
       severity: Literal["pass", "soft_fail", "hard_fail"]
       local_edit_targets: list[str]  # "冒頭3行" / "末尾段落" / "Day_5 段落2"
       per_category_evidence: dict[str, str]  # category → 証拠の引用
   ```
2. Generator の修正リトライは **失敗カテゴリ別の specialized prompt** で局所編集 (現状の全文書き直し → 問題箇所だけ書き直し)
3. `prompts/Prompt_Repair_<category>.md` を 5-7 個追加 (各 50 行以下)

**触るファイル**: `csdg/schemas.py`, `csdg/engine/critic.py`, `csdg/engine/actor.py`, `prompts/Prompt_Critic.md`, `prompts/Prompt_Repair_*.md` (新規)

**完了条件**:
- [ ] 失敗カテゴリの精度を generation_log.json で計測 (LLM-Judge の自己評価)
- [ ] 局所編集後のスコア改善が全文書き直しより**効率的** (API call 数 ↓、改善幅 ↑)

**工数**: 2-3 週間

**依存**: A-CRITICAL-1 (verdict)、A-HIGH-2 (Arc Plan があると series_incoherence カテゴリの判定精度 ↑)

---

### A-HIGH-4: llm_client.py の E2E テスト導入 (coverage 35% 解消)

**根拠**: pytest --cov 結果。AnthropicClient.generate_structured / Gemini フォールバック / リトライロジックが未テスト → `fix-overloaded-retry` `best-of-n-last-write-wins` 等の回帰バグが頻発。

**実装方針**:
1. `pytest-recording` または `vcr.py` で実 API レスポンスを記録 → CI で再生
2. `tests/integration/` を新設、`@pytest.mark.e2e` でマーク
3. CI workflow (Sprint 3 で構築) で `pytest -m "not e2e"` (高速) と `pytest -m "e2e"` (録画再生) を分離
4. AsyncAnthropic の `max_retries=5` と Pipeline 側 `max_retries=3` の **多重リトライ増幅問題** を確認・修正

**触るファイル**: `tests/integration/` (新規), `pyproject.toml` (pytest-recording 追加), `csdg/engine/llm_client.py`

**完了条件**:
- [ ] llm_client.py coverage 35% → **70%以上**
- [ ] OverloadedError, RateLimitError, schema mismatch 各ケースに E2E テストあり

**工数**: 1 週間

**依存**: なし (独立タスク、Sprint 5 で消化推奨)

---

### A-MEDIUM (5 件、概要のみ)

詳細は strict-review.md 参照。各タスクは 0.5-1 日。

| ID | 内容 | 触るファイル |
|---|---|---|
| MED-1 | Prompt_Generator.md (567 行) を 200 行以下に削減 | prompts/Prompt_Generator.md |
| MED-2 | pipeline.py 1319 行をサブモジュール分割 (`csdg/engine/pipeline/feedback.py`, `diversity.py`, `opening_pattern.py`, `ending_pattern.py`) | csdg/engine/pipeline.py |
| MED-3 | actor.py coverage 60% → 80% | csdg/engine/actor.py, tests/test_actor.py |
| MED-4 | critic.py のハードコード閾値 (_BASE_SCORE 等) を config.py に集約 | csdg/engine/critic.py, csdg/config.py |
| MED-5 | 動的 Skill 1 個追加 (例: `.claude/skills/recent-tasks/` で `!ls .steering/ \| tail -5`) | .claude/skills/recent-tasks/SKILL.md |

### A-LOW (3 件)

| ID | 内容 |
|---|---|
| LOW-1 | CharacterState を `frozen=True` 化 (現状: DailyEvent のみ frozen) |
| LOW-2 | prompt_loader.py に SHA-256 起動時バリデーション追加 |
| LOW-3 | visualization.py に critic_score_trajectory.png (T/E/P + retry のグラフ) 追加 |

---

## 4. ストリーム B: Persona Engine Pivot (戦略進化)

### B-Phase1: csdg/persona_engine/ + csdg/surfaces/diary/ への refactor

**根拠**: CSDG の独自貢献 (Pydantic 厳密型 × 認知物理 × narrative-quality Adversarial Critic) を engine 化することで、diary 以外の surface (内省 / 対話 / SNS 等) を生成可能にする。**車輪の再発明にならない** (Generative Agents / MemGPT / Concordia とは独自性の領域が異なる)。

**実装方針**:
```
csdg/                        # 現状
   ↓ refactor (機能変更なし、構造変更のみ)
csdg/persona_engine/         # ドメイン非依存コア
├── state.py                 # CharacterState, HumanCondition (現 schemas.py から抽出)
├── memory.py                # 現 memory.py 移行
├── transitions.py           # 現 state_transition.py 移行
└── arc_planner.py           # A-HIGH-2 で新設

csdg/surfaces/
└── diary/
    ├── generator.py         # 現 actor.py 移行
    ├── critic.py            # 現 critic.py 移行
    └── pipeline.py          # 現 pipeline.py 移行 (diary 専用部分)

csdg/critics/                # 評価器プール (将来 surface 横断)
└── narrative_quality.py     # diary に寄りすぎないように抽象化
```

**触るファイル**: `csdg/` 全体 (大規模 refactor)、すべての import path 更新、テストファイルの import path 更新

**完了条件**:
- [ ] 既存の 520 tests + E2E がすべて緑
- [ ] CLI コマンド `python -m csdg.main` の動作不変
- [ ] generation_log.json の構造不変
- [ ] docs/architecture.md, docs/repository-structure.md を refactor 後の構造に更新

**工数**: 2 週間 (機能変更なし、移動のみ)

**依存**: A-CRITICAL-1 + A-HIGH-1 完了後 (refactor 中の不安定期にバグ修正が重ならないように)

---

### B-Phase2: 第 2 surface 追加 (csdg/surfaces/reflection/)

短い内的独白 (100-200 字) を不定期生成する surface。Engine の汎用性を実証する目的。

**触るファイル**: `csdg/surfaces/reflection/` (新規 3 ファイル: generator.py, critic.py, pipeline.py), `prompts/Prompt_Reflection.md` (新規)

**完了条件**: 同一 CharacterState から diary + reflection 両方が引き出せる

**工数**: 1 週間

**依存**: B-Phase1 完了

---

### B-Phase3: 軽量 world.py 追加

`csdg/persona_engine/world.py` に時刻 / 場所 / NPC を最小限保持。CRITICAL-2 (ドメイン語彙ハードコード) の自然な解決にもなる。

```python
class World(BaseModel):
    time_of_day: Literal["morning", "afternoon", "evening", "night"]
    current_location: str
    present_npcs: dict[str, NPCState]  # name → NPC 状態
    weather: str | None = None
```

**触るファイル**: `csdg/persona_engine/world.py` (新規), `prompts/ontology/places.yaml`, `prompts/ontology/objects.yaml`, `prompts/ontology/voices.yaml` (新規、CRITICAL-2 解消)

**工数**: 1-2 週間

**依存**: B-Phase1 完了

---

## 5. ストリーム C: OSS Hygiene

### C-Phase1: CRITICAL — LICENSE + 法的最低限 (30 分-1 時間)

リポジトリは既に GitHub で公開されているにもかかわらず LICENSE 不在 → 法的にデフォルト「全権利留保」状態。利用者が fork / 引用 / 転用 すべて不明。**最優先で対応すべき**。

**dual licensing**:
| 対象 | ライセンス | 理由 |
|---|---|---|
| コード (csdg/, tests/, scripts/) | **Apache-2.0** | Anthropic SDK 等と整合、特許保護、企業利用フレンドリー |
| プロンプト・ペルソナ (prompts/, docs/) | **CC BY-NC-SA 4.0** | キャラクター IP 保護 + 学術/個人利用許可、商用転用には別途許諾 |

**生成ファイル**:
1. **`LICENSE`** — Apache-2.0 全文 (`https://www.apache.org/licenses/LICENSE-2.0.txt`)
2. **`LICENSE-CONTENT`** — CC BY-NC-SA 4.0 全文 (or リンクのみ)
3. **`NOTICE`** — Apache-2.0 採用時の依存ライブラリ帰属:
   ```
   CSDG (Cognitive-State Diary Generator)
   Copyright 2026 [著者名]

   This product includes software developed by:
   - Anthropic, PBC (Anthropic SDK, Apache-2.0)
   - Pydantic Services Inc. (Pydantic, MIT)
   - Google LLC (Google Generative AI Python SDK, Apache-2.0)
   ...
   ```
4. **`pyproject.toml`** に license フィールド追加:
   ```toml
   [project]
   name = "csdg"
   license = { text = "Apache-2.0" }
   ```
5. **`README.md`** に「License」セクション追加:
   ```markdown
   ## License

   - **Code** (csdg/, tests/, scripts/): [Apache-2.0](LICENSE)
   - **Prompts and Persona Content** (prompts/, persona definitions): [CC BY-NC-SA 4.0](LICENSE-CONTENT)
   - **Generated Diary Outputs** (output/): subject to LLM provider terms (Anthropic / Google) + CC BY-NC-SA 4.0
   ```

**完了条件**:
- [ ] LICENSE / LICENSE-CONTENT / NOTICE が repo root に存在
- [ ] pyproject.toml が license を宣言
- [ ] README.md に License セクション
- [ ] GitHub UI 上で「Apache-2.0」バッジが表示される
- [ ] 著者名 (Copyright holder) を確定して LICENSE / NOTICE に反映

**工数**: 30 分-1 時間 (Apache-2.0 / CC BY-NC-SA 4.0 はテンプレ流用可)

**未確定要素**: 著作権者名 (個人 or 組織)。新セッション開始時にユーザーに確認必須。

---

### C-Phase2: HIGH — SECURITY + CONTRIBUTING + CI (1-2 日)

**生成ファイル**:

6. **`SECURITY.md`**:
   ```markdown
   # Security Policy

   ## Reporting a Vulnerability

   Use [GitHub Private Vulnerability Reporting](https://github.com/.../security/advisories/new) for any security issues.
   Do NOT open public issues for vulnerabilities.

   Expected response time: 7 days.

   ## Scope
   - API key handling (never log / commit / send to external LLM)
   - Prompt injection in user-provided event descriptions
   - Schema validation bypasses
   ```

7. **`CONTRIBUTING.md`**:
   ```markdown
   # Contributing to CSDG

   ## Workflow
   1. Fork → branch (feat/<area>-<desc> or fix/<area>-<id>)
   2. Follow CLAUDE.md / docs/development-guidelines.md
   3. Add tests for new features (see docs/development-guidelines.md §Testing)
   4. Run: `pytest tests/ -v && mypy csdg/ --strict && ruff check csdg/`
   5. Submit PR with DCO sign-off (`git commit -s`) — no CLA required for Apache-2.0
   6. Optional: `/cross-review` for important PRs (Codex independent review)

   ## Style
   - Pydantic v2 strict typing
   - prompts/ external markdown only (no Python code embedded)
   - Pre-commit: ruff format + ruff check
   ```

8. **`README.md` に「Ethics / Acceptable Use」セクション追加**:
   ```markdown
   ## Ethics / Acceptable Use

   CSDG generates LLM-driven character text. The following are NOT acceptable uses:
   - Impersonation of real people
   - Hate speech, harassment, or disinformation generation
   - User personalization without explicit consent
   - Use as a replacement for professional mental-health advice

   The character "三浦とこみ" is a fictional persona; all generated diary outputs are AI-produced fiction.
   ```

9. **`.github/ISSUE_TEMPLATE/bug_report.yml`**:
   ```yaml
   name: Bug Report
   description: Report a bug or unexpected behavior
   body:
     - type: textarea
       attributes:
         label: Description
     - type: textarea
       attributes:
         label: Reproduction steps
     - type: textarea
       attributes:
         label: Expected vs actual
     - type: input
       attributes:
         label: Python version
     - type: textarea
       attributes:
         label: generation_log.json (sanitized)
   ```

10. **`.github/ISSUE_TEMPLATE/feature_request.yml`** (類似フォーマット)

11. **`.github/PULL_REQUEST_TEMPLATE.md`**:
    ```markdown
    ## Summary
    <!-- 1-3 bullets -->

    ## Test plan
    - [ ] pytest tests/ -v
    - [ ] mypy csdg/ --strict
    - [ ] ruff check csdg/
    - [ ] /verify-setup (環境構築変更時)

    ## Related steering task
    `.steering/[YYYYMMDD]-<task>/`
    ```

12. **`.github/workflows/ci.yml`**:
    ```yaml
    name: CI
    on: [push, pull_request]
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: astral-sh/setup-uv@v3
          - run: uv sync
          - run: uv run pytest tests/ -v -m "not e2e" --cov=csdg
          - run: uv run mypy csdg/ --strict
          - run: uv run ruff check csdg/
          - run: uv run ruff format --check csdg/
    ```

**触るファイル**: 上記 7 ファイル (新規)

**完了条件**:
- [ ] GitHub UI で「Security policy」「Contributing」リンクが表示
- [ ] CI が PR 上で実行され、mypy/ruff/pytest 全部緑
- [ ] Issue / PR が template から作成可能

**工数**: 1-2 日

**依存**: C-Phase1 完了 (LICENSE が決まっていないと CONTRIBUTING の DCO 表記が確定しない)

---

### C-Phase3: MEDIUM — Code of Conduct + Citation + Changelog (1 日)

13. **`CODE_OF_CONDUCT.md`** — Contributor Covenant 2.1 (テンプレ差し替えのみ、`<email>` を確定)
14. **`CITATION.cff`**:
    ```yaml
    cff-version: 1.2.0
    title: CSDG - Cognitive-State Diary Generator
    authors:
      - family-names: <surname>
        given-names: <given>
        orcid: <if applicable>
    repository-code: https://github.com/mikotomiura/cognitive-state-diary-generator
    license: Apache-2.0
    keywords: [LLM, narrative generation, Actor-Critic, Pydantic, cognitive state]
    abstract: >
      An adversarial Actor-Critic pipeline for generating literary character diaries
      with Pydantic-strict cognitive state modeling.
    ```
15. **`CHANGELOG.md`** — Keep a Changelog 形式、過去のコミットから 0.1.0 リリース履歴を作成

**工数**: 0.5-1 日

---

### C-Phase4: LOW — SPDX ヘッダー + バッジ (0.5 日)

16. csdg/ 配下の Python ファイル冒頭に SPDX 識別子追加:
    ```python
    # SPDX-License-Identifier: Apache-2.0
    # Copyright 2026 [著者名]
    ```
17. README.md にバッジ追加:
    ```markdown
    ![License](https://img.shields.io/badge/license-Apache%202.0-blue)
    ![Content License](https://img.shields.io/badge/content-CC%20BY--NC--SA%204.0-green)
    ![Python](https://img.shields.io/badge/python-3.11+-blue)
    ![Tests](https://img.shields.io/badge/tests-520%20passing-brightgreen)
    ![Coverage](https://img.shields.io/badge/coverage-85%25-green)
    ```

**工数**: 0.5 日

---

## 6. 全体まとめ

### 完了時の状態 (理想形)

```
csdg/                            # ストリーム B 完了後
├── persona_engine/              # ドメイン非依存コア (engine としての独立性)
│   ├── state.py
│   ├── memory.py
│   ├── transitions.py
│   ├── arc_planner.py           # A-HIGH-2
│   └── world.py                 # B-Phase3, CRITICAL-2 解消も兼ねる
├── surfaces/
│   ├── diary/                   # 既存機能の retrofit
│   ├── reflection/              # B-Phase2 で追加
│   └── ... (将来)
└── critics/
    ├── narrative_quality.py     # 診断器 (A-HIGH-3)
    └── voice_consistency.py

prompts/
├── ontology/                    # CRITICAL-2 解消、データ駆動
│   ├── places.yaml
│   ├── objects.yaml
│   └── voices.yaml
├── Prompt_ArcPlan.md            # A-HIGH-2
├── Prompt_Repair_*.md           # A-HIGH-3 (失敗カテゴリ別)
└── ... (既存)

リポジトリ root:
├── LICENSE (Apache-2.0)         # C-Phase1
├── LICENSE-CONTENT (CC BY-NC-SA 4.0)
├── NOTICE
├── SECURITY.md                  # C-Phase2
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md           # C-Phase3
├── CITATION.cff
├── CHANGELOG.md
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/ci.yml
└── README.md (License / Ethics 節を含む)
```

### KPI / 観測指標

| 指標 | 現状 | 30 日目標 | 90 日目標 |
|---|---|---|---|
| Critic スコア 5 出現率 | 0% | 10% | 25% |
| Critic スコア 3 出現率 (cliff edge) | 62% | 40% | 25% |
| pipeline.py 行数 | 1,319 | 1,000 | 700 |
| llm_client.py coverage | 35% | 60% | 80% |
| E2E テスト数 | 0 | 5 | 15 |
| Surface 数 | 1 (diary) | 1 | 2 (+ reflection) |
| LICENSE 整備 | 不在 | C-Phase1+2 完了 | C-Phase4 完了 |

---

## 7. 新セッションでのアクションテンプレ

新セッション開始時に以下を実行:

```bash
# 1. このファイルと strict-review を読む
cat .steering/20260507-system-strict-review/improvement-plan.md
cat .steering/20260507-system-strict-review/strict-review.md

# 2. ユーザーに「どの Sprint から?」を確認
# → Sprint 1 (C-Phase1, OSS) を推奨。並行で Sprint 2 (A-CRITICAL-1) も可

# 3. 該当 Sprint の新タスクを起こす
/start-task
# → タスク名例: 20260508-license-and-oss-hygiene または 20260508-critic-verdict
# requirement.md に必ず親レポート参照を含める
# requirement.md の「親レポート」欄: .steering/20260507-system-strict-review/

# 4. 実装 → /implement <type>

# 5. 重要 PR は /cross-review で Codex 第二意見

# 6. /finish-task でコミット
```

### 新セッションが知らないこと (本ファイルに書ききれない暗黙知)

- `.steering/20260507-system-strict-review/` の存在意義
- Codex (gpt-5.5, 13609 tokens 使用済) との独立確認の重要性
- 「6 週間 30 サイクルで plateau」「mole-whacking limit」memory note の意味
- ユーザーの戦略意図 (diary だけでなく persistent persona engine への進化志向)

これらは本ファイル + strict-review.md + memory (`feedback_prompt_tuning_limits.md`) を読めば再構築可能。

---

**最終ノート**: 本セッションは Phase 5 (Codex Bridge) 構築 + 環境整備 refactor + 戦略レビュー + OSS hygiene 計画立案 を完了した。総コミット 5 (PR #14 マージ済)。Codex の独立第二意見と Claude の主分析が完全一致し、提言の信頼性は高い。次セッションでは Sprint 1 (OSS Phase 1) または Sprint 2 (A-CRITICAL-1) から、コンテキストをリセットして自己完結的に着手すること。
