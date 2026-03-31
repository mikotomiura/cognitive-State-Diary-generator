# CSDG - Cognitive-State Diary Generator

体系的認知モデルに基づく AI キャラクター日記生成システム。
Actor-Critic 型の敵対的検証ループにより、7 日間の一人称ブログ日記を自動生成する。

## 概要

CSDG は、架空のキャラクター「三浦とこみ」(26 歳、バックエンドエンジニア / 元哲学大学院生) の内面を
構造化された認知状態モデルとして管理し、日々のイベントに対する感情変化と日記テキストを生成する。

### 3-Phase パイプライン

```
Day 1 〜 Day 7 ループ:

  Phase 1: State Update     ─ イベント x_t から内部状態 h_t を更新
       ↓                      (半数式化: 決定論的骨格 + LLM delta 補正)
  Phase 2: Content Gen      ─ h_t に基づきブログ日記テキストを生成
       ↓
  Phase 3: Critic Eval      ─ 3層評価 (RuleBased / Statistical / LLMJudge)
       ↓
  Pass → 保存 / Reject → リトライ (最大3回, Temperature Decay)
```

### 主な特徴

- **状態空間モデル** -- 感情パラメータを管理 (fatigue: `0.0`〜`1.0`、motivation/stress: `-1.0`〜`1.0`)
- **半数式化された状態遷移** -- 決定論的な数式ベース + LLM による解釈的補正で再現性を確保
- **3 層 Critic + 段階化ボーナス** -- ルールベース検証 (L1) + 統計的検証 (L2) + LLM 定性評価 (L3) の重み付き統合 (0.40 / 0.35 / 0.25)。L1/L2 の各指標に sweet spot / acceptable / penalty の 3 段階ボーナスを設け、加重平均が integer 境界を跨ぐ十分な帯域幅を確保。base score 2.5 と組み合わせ、最終スコアの弁別力 (5 種類以上のユニークパターン) を実現
- **2 層メモリ** -- 短期記憶 (直近 3 日) + 長期記憶 (信念・テーマ・転換点)
- **余韻フィードバック** -- 直近 3 日の末尾段落を抽出・蓄積し、生成プロンプトに注入することで余韻フレーズの反復を防止。余韻間の trigram 類似度チェックにより、異なるキーワードでも意味的に類似した締めくくりを検出・抑制。生成プロンプト側では Step 1 (固有物選択) → Step 2 (固有物への問い) → Step 3 (前日比較) の 3 段階手順と構文頻度制限を適用
- **シーン描写の反復防止** -- 場所・物のマーカー語を含むキーフレーズを Day 間で蓄積し、イメージの使い回しを抑制
- **場面構造パターン追跡** -- 帰路型 / 古書店型 / 会議型 等の場面構造を自動分類・蓄積し、「帰り道→電車→自宅」パターンの過剰使用 (7 日間で最大 2 回) を防止
- **哲学者引用カウンター** -- 日記内の哲学者・思想家への言及を Day 間で蓄積し、同一人物への過剰言及 (7 日間で最大 2 回) を防止
- **書き出しパターンの多様化** -- 比喩型 / 五感型 / 会話型 / 問い型 / 断片型 / 回想型 の 6 パターンを自動分類・蓄積し、書き出しの単調化を防止
- **Self-Healing** -- LLM 出力のパースエラーに対するリトライ + Best-of-N フォールバック + API 過負荷時の指数バックオフリトライ

## セットアップ

### 前提条件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (推奨) または pip

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/mikotomiura/cognitive-State-Diary-generator.git
cd cognitive-State-Diary-generator

# 依存関係のインストール
uv sync

# 環境変数を設定
cp .env.example .env
# .env を編集し CSDG_LLM_API_KEY に Anthropic API キーを設定
```

### 環境変数

| 変数名 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `CSDG_LLM_API_KEY` | Yes | - | Anthropic API キー |
| `CSDG_LLM_MODEL` | No | `claude-sonnet-4-20250514` | 使用する Claude モデル |
| `CSDG_MAX_RETRIES` | No | `3` | Critic Reject 時の最大リトライ回数 |
| `CSDG_INITIAL_TEMPERATURE` | No | `0.7` | 初回生成の Temperature |
| `CSDG_OUTPUT_DIR` | No | `output` | 出力ディレクトリ |

## 使い方

### 全 7 日分を生成

```bash
python -m csdg.main
```

### 特定の Day のみ実行

```bash
python -m csdg.main --day 4
```

### オプション

```bash
python -m csdg.main --help

# --day N              特定の Day のみ実行
# --output-dir PATH    出力先ディレクトリを指定
# --verbose            デバッグログを出力
# --skip-visualization グラフ生成をスキップ
# --dry-run            設定確認のみ (API 呼び出しなし)
```

### 出力

```
output/
  day_01.md 〜 day_07.md    # 生成された日記 (YAML frontmatter + Markdown)
  generation_log.json       # 実行ログ (リトライ数、スコア推移等)
  critic_log.jsonl          # Critic 評価ログ (JSON Lines)
  state_trajectory.png      # 感情パラメータ + CriticScore の推移グラフ
```

### Critic 弁別力の検証

```bash
python scripts/verify_critic_discrimination.py output/generation_log.json
```

`generation_log.json` と `critic_log.jsonl` から L1/L2/L3 のスコア分散・最終スコアのレンジ・ユニークパターン数を計算し、弁別力の目標値 (L1/L2 標準偏差 > 0.3、ユニークスコアパターン >= 3) を満たしているか判定する。

## アーキテクチャ

### モジュール構成

```
csdg/
  schemas.py              # Pydantic データモデル (CharacterState, CriticScore 等)
  config.py               # 環境変数ベースの設定管理
  scenario.py             # 7日分のイベント + 初期状態
  engine/
    actor.py              # Phase 1 (状態更新) + Phase 2 (日記生成)
    critic.py             # Phase 3 (3層評価: RuleBased / Statistical / LLMJudge)
    critic_log.py         # CriticLog 蓄積・フィードバック注入
    state_transition.py   # 半数式化された状態遷移 (decay + event + LLM delta)
    memory.py             # 2層メモリ (ShortTerm + LongTerm)
    pipeline.py           # パイプライン制御 (リトライ / Temperature Decay / Best-of-N)
    llm_client.py         # LLM API 抽象化 (Anthropic Claude 実装)
    prompt_loader.py      # プロンプトファイル読み込みユーティリティ
  main.py                 # CLI エントリポイント
  visualization.py        # 状態推移グラフ生成

scripts/
  verify_critic_discrimination.py  # Critic 弁別力検証スクリプト

prompts/
  System_Persona.md       # キャラクター定義 (三浦とこみ)
  Prompt_StateUpdate.md   # Phase 1 プロンプト
  Prompt_Generator.md     # Phase 2 プロンプト
  Prompt_Critic.md        # Phase 3 プロンプト
  Prompt_MemoryExtract.md # 長期記憶の信念・テーマ抽出
  System_MemoryManager.md # メモリ管理システムプロンプト
```

### Critic 3 層構造

| 層 | クラス | 種別 | 重み | 検証内容 |
|---|---|---|---|---|
| Layer 1 | `RuleBasedValidator` | 決定論的 | 0.40 | 文字数 (段階化)、わたし使用頻度 (段階化 + 過剰使用ペナルティ)、余韻「......」(段階化)、前日重複率 (段階化)、感情 deviation 5 段階評価 (増強ペナルティ)、余韻 trigram 類似度 |
| Layer 2 | `StatisticalChecker` | 数値的 | 0.35 | 平均文長 (段階化)、句読点頻度 (段階化)、文数 (段階化)、疑問文比率 (段階化)、deviation 連続スケーリング (増強ペナルティ)、断定文比率、高インパクト日文体検証 |
| Layer 3 | `LLMJudge` | 定性的 | 0.25 | LLM による temporal / emotional / persona 評価 (L1/L2 結果を参照基準として構造化注入) |

#### 段階化ボーナスによる弁別力確保

L1/L2 の各検証指標に sweet spot / acceptable / penalty の 3 段階を設け、ボーナス幅を拡大:

```
例: わたし使用頻度 (L1 persona_deviation)
  [4, 6] → +1.0 (sweet spot)
  [2, 8] → +0.5 (acceptable)
  > 8    → -1.0 (overuse penalty)

例: 句読点頻度 (L2 temporal_consistency)
  [0.070, 0.080] → +1.0 (sweet spot)
  [0.060, 0.090] → +0.5 (acceptable)
```

最終スコアは純粋な加重平均の `round()` で決定 (base score 2.5):

```
final = clamp(round(L1 × 0.40 + L2 × 0.35 + L3 × 0.25), 1, 5)
```

これにより L1/L2 のレイヤースコアが 2.0〜4.5 の広い帯域幅を持ち、最終スコアの弁別力 (5 種類以上のユニークパターン) を確保する。

### 状態遷移の数式

```
base[param] = prev[param] * (1 - decay_rate) + event_impact * event_weight
h_t[param]  = base + llm_delta[param] * llm_weight + noise
clamp(h_t[param], lo, 1.0)    # lo = 0.0 for fatigue, -1.0 for others
```

## 開発

### テスト

```bash
# 全テスト実行
pytest tests/ -v

# カバレッジ付き
pytest tests/ -v --cov=csdg
```

### 型チェック・リンター

```bash
# 型チェック (strict mode)
mypy csdg/ --strict

# リンター
ruff check csdg/

# フォーマッター
ruff format csdg/
```

### シナリオ (7 日間のイベント)

| Day | event_type | impact | 概要 |
|---|---|---|---|
| 1 | neutral | +0.2 | 自動化スクリプト完成、虚しさ |
| 2 | positive | +0.6 | 古書店で西田幾多郎の初版本を発見 |
| 3 | negative | -0.5 | コードレビュー会で設計提案を一蹴される |
| **4** | **negative** | **-0.9** | **全社 AI 自動化ロードマップ発表 (転機)** |
| 5 | neutral | +0.15 | ミナとの会話で「あなたは表現者だ」 |
| 6 | neutral | +0.5 | 大学院時代の現象学ノートを発見 |
| 7 | positive | +0.5 | 暗黙知の可視化を職場に提案 |

## ライセンス

MIT
