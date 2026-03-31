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
- **3 層 Critic + コンセンサス補正** -- ルールベース検証 + 統計的検証 + LLM 定性評価の重み付き統合。L1/L2 の決定論的シグナルと L3 (LLM) の乖離を増幅する「L1/L2 コンセンサス補正」により、LLM の保守的採点 (全 Day 4/4/4) を補正し、最終スコアの弁別力を確保
- **2 層メモリ** -- 短期記憶 (直近 3 日) + 長期記憶 (信念・テーマ・転換点)
- **余韻フィードバック** -- 直近 3 日の末尾段落を抽出・蓄積し、生成プロンプトに注入することで余韻フレーズの反復を防止。余韻間の trigram 類似度チェックにより、異なるキーワードでも意味的に類似した締めくくりを検出・抑制
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

生成ログから L1/L2/L3 のスコア分散・最終スコアのレンジを計算し、弁別力の目標値 (L1/L2 標準偏差 > 0.3、最終スコアレンジ >= 2) を満たしているか判定する。

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
| Layer 1 | `RuleBasedValidator` | 決定論的 | 0.35 | 文字数、絵文字、重複率、方向整合性、余韻 trigram 類似度、感情 deviation 5 段階評価 |
| Layer 2 | `StatisticalChecker` | 数値的 | 0.30 | 平均文長、句読点頻度、文数、deviation 連続スケーリング、断定文比率、高インパクト日文体検証 |
| Layer 3 | `LLMJudge` | 定性的 | 0.35 | LLM による temporal / emotional / persona 評価 (L1/L2 結果を参照基準として構造化注入) |

#### L1/L2 コンセンサス補正

最終スコア算出時、L1/L2 の加重平均と L3 の乖離を検出し、L1/L2 方向に 50% 増幅する。

```
l12_norm    = (L1 × w1 + L2 × w2) / (w1 + w2)
correction  = (l12_norm − L3) × 0.5
final_raw   = weighted_avg + correction
final       = clamp(round(final_raw), non_amplified ± 1)
```

これにより、L3 が保守的に 4/4/4 を返す場合でも、L1/L2 の客観的評価が最終スコアに反映される。

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
