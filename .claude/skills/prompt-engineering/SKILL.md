---
name: prompt-engineering
description: >
  CSDG プロジェクトにおける LLM プロンプト設計の原則とベストプラクティス。
  prompts/ のMarkdownファイルを作成・修正する際、
  Actor/Critic の出力品質を改善する際に参照する。
  ペルソナ設計、状態遷移指示、日記生成指示、評価基準設計、
  Structured Outputs 対応、Temperature戦略を包括的にカバーする。
allowed-tools: Read, Grep, Glob
---

# LLM プロンプト設計原則

## 基本原則

1. **プロンプトはコードに埋め込まない** — `prompts/` の外部Markdownファイルで管理する
2. **役割を分離する** — Actor（生成）と Critic（評価）は異なるプロンプトで動作する
3. **具体的に指示する** — 「良い文章を書いて」ではなく「壮大な比喩を1段落に最低1つ含めて」
4. **否定形より肯定形** — 「〜しないで」より「〜してください」が効果的
5. **用語を統一する** — `glossary.md` の定義に従い、プロンプト内の用語を一致させる

---

## CSDG のプロンプト構成

| ファイル | 役割 | Phase | 出力形式 |
|---|---|---|---|
| `System_Persona.md` | 不変のキャラクタールール | 全Phase (System) | — |
| `Prompt_StateUpdate.md` | 感情遷移の計算指示 | Phase 1 (User) | JSON (Structured Outputs) |
| `Prompt_Generator.md` | 日記の文章生成指示 | Phase 2 (User) | テキスト (Markdown) |
| `Prompt_Critic.md` | 評価基準と採点指示 | Phase 3 (User) | JSON (Structured Outputs) |

---

## プロンプト注入順序

```
[System Prompt]
  └─ System_Persona.md（常に先頭。意味記憶として機能）

[User Prompt]
  ├─ Phase固有のプロンプト（Prompt_*.md）
  ├─ 動的データ（JSON: state, event, memory_buffer等）
  └─ (リトライ時) 修正指示（revision_instruction）
```

**重要:** System Prompt にペルソナ定義を置くことで、User Prompt の内容が変わっても人格の一貫性が保たれる。

---

## プロンプト設計のポイント

### System_Persona.md — ペルソナの不変ルール

- キャラクターの「核」を最初に定義する（性格、矛盾、思考パターン）
- 禁則事項を明確にリスト化する（絵文字禁止、断定禁止等）
- 口調ルールを具体例付きで記述する
- 「こう書いてはいけない」例を含める

### Prompt_StateUpdate.md — 状態遷移の指示

- emotional_impact の値とパラメータ変動の関係を数式で明示する
- memory_buffer の参照方法を具体的に指示する
- 各フィールドの更新ルールを個別に記述する

### Prompt_Generator.md — 日記生成の指示

- 文体ルールを具体例で示す（壮大な比喩、感情爆発時の短文連打等）
- 日記の構成要素を指示する（冒頭、展開、余韻）
- emotional_impact の大きさに応じた文体の変化を指示する

### Prompt_Critic.md — 評価基準の設計

- 1〜5の各スコアの具体的な判定基準を記述する
- 合格ライン（3以上）を明示する
- Reject時には具体的な修正指示を出すよう指示する
- expected_delta と deviation の使い方を説明する

---

## Temperature 戦略

| 状況 | Temperature | 理由 |
|---|---|---|
| Phase 1（状態遷移）初回 | 0.7 | ある程度の多様性を持たせる |
| Phase 2（日記生成）初回 | 0.7 | 文学的な表現の多様性 |
| Phase 3（Critic評価） | 0.3 | 評価の安定性を重視 |
| リトライ1回目 | 0.5 | やや保守的に |
| リトライ2回目 | 0.3 | 決定論的に |

---

## 補足資料

- `examples.md` — 各プロンプトファイルの実装例とテンプレート
- `evaluation-guide.md` — プロンプトの品質評価と改善手法
