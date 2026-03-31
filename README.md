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
- **余韻フィードバック** -- 直近 3 日の末尾段落を抽出・蓄積し、生成プロンプトに注入することで余韻フレーズの反復を防止。余韻間の trigram 類似度チェックにより、異なるキーワードでも意味的に類似した締めくくりを検出・抑制。生成プロンプト側では Step 1 (固有物選択) → Step 2 (固有物への問い) → Step 3 (前日比較) の 3 段階手順と構文頻度制限を適用。さらに「この〇〇は、どんな△△を〜だろう」等のテンプレート化しやすい余韻構文を禁止リストで管理し、体言止め・倒置・描写締め・行動締め等 7 種の多様な余韻パターン例を提示
- **シーン描写の反復防止** -- 場所・物のマーカー語 (30 語: 万年筆 / 茶碗 / 珈琲 / 背表紙等のキャラクタ世界観に即した具体物) を含むキーフレーズを Day 間で蓄積し、イメージの使い回しを抑制。誤検出しやすい汎用語 (「本」「道」等) は除外済み
- **場面構造パターン追跡 + 連続使用検出** -- 帰路型 / 古書店型 / 会議型 等の場面構造を自動分類・蓄積し、全パターンの出現回数をカウント (帰路型・古書店型は最大 2 回、他は最大 3 回)。前日と同一構造の連続使用を検出し禁止。使用可能な代替構造 (自室内省型 / 移動中思索型 / 対話中心型 / 回想主導型) を提示。Critic Pass 時でも場面構造違反がある場合は 1 回限定で再試行を強制
- **哲学者引用カウンター** -- 日記内の哲学者・思想家への言及を Day 間で蓄積し、同一人物への過剰言及 (7 日間で最大 2 回) を防止
- **書き出しパターンの多様化 + ホワイトリスト注入** -- 比喩型 / 五感型 / 会話型 / 問い型 / 断片型 / 回想型 の 6 パターンを自動分類・蓄積し、書き出しの単調化を防止。余韻と同様の**ホワイトリスト + 具体例**方式で使用可能パターンと残り回数を提示。Markdown 見出し行・日付行をスキップして実質的な冒頭行を判定。冒頭イメージはその日のイベントから自然に導かれることを必須とし、イベントと無関係な場所・物を使う場合は本文中での回収を義務付け
- **概念語の頻度制御** -- 同一概念語 (例: 「効率」「非効率」「効率化」「効率的」) の 1 エントリあたりの使用回数を最大 3 回に制限し、growth_theme の単純な二項対立への矮小化を防止。超過分は言い換え語彙への置換を指示
- **余韻構文パターン追跡 + ホワイトリスト注入** -- 余韻の末尾構文を「〜だろう系 / 〜かもしれない系 / 〜ずにいる系 / 〜ている系 / 行動締め系 / 引用系 / 体言止め系 / 省略系 / その他」の 9 パターンに自動分類・蓄積。使用禁止パターンの列挙 (ブラックリスト) ではなく、**使用可能パターンと具体例の列挙 (ホワイトリスト)** 方式でプロンプトに注入し、LLM の余韻多様性を誘導
- **主題語の累計頻度制御** -- 主題語 (「効率」「非効率」「最適化」「自動化」) の 7 日間累計使用回数を追跡し、ソフトリミット (10 回) 超過で per-day 制限を強化、ハードリミット (18 回) 超過で使用禁止。Day 1 から per-day 制限 (3 回/日) を常時注入し、コールドスタート問題を解消。イベント記述に主題語が含まれる場合は「日記本文では代替表現に置き換えてください」と明示的に警告注入
- **修辞疑問文の反復防止** -- 本文中の「〜って、何に対して？」「〜のため？」「〜なのか」「〜のだろうか」等の修辞疑問文を抽出・蓄積し (直近 5 件)、同一構文の Day 間再使用を禁止
- **シーンマーカー出現日数追跡** -- 場所・物のマーカー語 (「蛍光灯」「キーボード」等) の出現日数を Day 間で追跡し、2 日以上の出現で使用自粛、3 日以上で使用禁止を注入。フレーズレベルの `prev_images` では防げないマーカー語レベルの反復を制御
- **高インパクト日の Temperature 維持** -- |emotional_impact| > 0.7 の高インパクト日で persona_deviation が不合格のリトライ時、Temperature を下げずに初期値 (0.7) を維持。文体の多様性が求められる場面での Temperature Decay 逆効果を防止
- **日跨ぎフレーズ重複防止** -- 余韻だけでなく本文中の修辞疑問文・印象的フレーズも Day 間で重複チェックの対象とし、同一構文の連日使用を禁止。Critic 側でも本文フレーズの日跨ぎ重複を temporal_consistency の検出ポイントに追加
- **高インパクト日の文体必須条件** -- |emotional_impact| > 0.7 の日に対し、6 文字以下の短文 3 連続 (短文連打) を必須要件として明確化。Critic 側では短文連打の有無を persona_deviation スコア上限の決定因子とし、欠如時は他条件を満たしていても最大 3 に制限
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

### 品質制御アーキテクチャ (正規化項)

品質向上は生成時の制約注入 (Pipeline → Actor Prompt) で実現し、Critic は安全弁 (リトライ判定) に留める設計。

```
[生成時正規化 (Pipeline → Actor Prompt)]
  ├── 冒頭禁止事項 (critical_constraints: プロンプト先頭に配置)
  │   ├── 余韻パターン上限到達 → 使用禁止
  │   ├── 場面構造の前日同一 → 使用禁止
  │   ├── 場面構造の上限到達 → 使用禁止
  │   └── 書き出しパターン上限到達 → 使用禁止
  │
  ├── ホワイトリスト注入 (使用可能パターン + 具体例 + 残り回数)
  │   ├── used_ending_patterns  ... 余韻: 9パターン分類, 具体例付き
  │   └── used_openings         ... 書き出し: 6パターン分類, 具体例付き
  │
  ├── L1 正規化 (スパース化 = パターン禁止)
  │   ├── used_structures       ... 場面構造: 全パターン追跡 + 連続使用検出 + 代替提示
  │   ├── used_philosophers     ... 哲学者引用反復防止 (同一人物≤2回)
  │   └── prev_rhetorical       ... 修辞疑問反復防止 (直近5件)
  │
  ├── L2 正規化 (平滑化 = 頻度制限)
  │   ├── prev_endings          ... 余韻フレーズ反復抑制 (直近3日)
  │   ├── prev_images           ... シーン描写反復抑制 (最大5件, 30語マーカー)
  │   ├── theme_word_totals     ... 主題語過剰使用抑制 (soft/hard limit)
  │   └── scene_marker_days     ... シーンマーカー出現日数 (2日自粛/3日禁止)
  │
  └── Dropout 的正規化 (使用上限による強制多様化)
      ├── 書き出し: 比喩型≤2回, 他≤3回
      ├── 帰路型/古書店型: ≤2回, 他≤3回
      ├── 哲学者: 同一人物≤2回
      └── 余韻構文: 同一パターン≤2回

[生成後バリデーション (構造的制約チェック)]
  ├── _validate_structural_constraints() で5項目を軽量検査
  │   ├── 余韻パターン上限 (2回超過?)
  │   ├── 場面構造の連続使用 (前日と同一?)
  │   ├── 場面構造の上限超過?
  │   ├── 主題語 per-day 上限 (3回/日超過?)
  │   └── 書き出しパターン上限超過?
  │
  ├── Critic Reject 時 → 違反内容をリビジョン指示に合流して次回リトライに注入
  ├── Critic Pass + 場面構造違反 → 1回だけ再試行 (structural_retry)
  └── Critic Pass + 他の違反のみ → 警告ログ出力、日記は採用

[事後評価 (Critic = 安全弁)]
  ├── Layer 1 (RuleBased): 致命的違反の検出 + veto
  ├── Layer 2 (Statistical): 文体統計の異常検出
  └── Layer 3 (LLMJudge): 定性的品質チェック
  → リトライ判定のみ。品質向上の主力ではない。
```

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
