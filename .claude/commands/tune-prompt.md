# /tune-prompt — プロンプトチューニングワークフロー

> **目的:** 生成品質の向上のため、`prompts/` のプロンプトファイルを調整する。
> **粒度:** 1つのプロンプトファイルに対する1つの改善目的。
> **鉄則:** プロンプト変更はコード変更を伴わないことが望ましい。伴う場合は `/add-feature` に切り替える。

---

## ステップ 1: 問題の特定

1. **`log-analyzer` サブエージェントを起動する:**
   - `output/generation_log.json` を分析する
   - 低スコアのDayを特定する
   - Reject原因（`reject_reason`）のパターンを分析する

2. **問題の分類:**

   | 問題の種類 | 対応するプロンプト | CriticScore の低い軸 |
   |---|---|---|
   | 過去の出来事との矛盾 | `Prompt_StateUpdate.md` / `Prompt_Generator.md` | `temporal_consistency` |
   | 感情変化が不自然 | `Prompt_StateUpdate.md` | `emotional_plausibility` |
   | キャラクターらしさが薄い | `System_Persona.md` / `Prompt_Generator.md` | `persona_deviation` |
   | 評価基準が厳しすぎる/甘すぎる | `Prompt_Critic.md` | 全体的にスコアが偏る |
   | 日記の文学的品質が低い | `Prompt_Generator.md` | （CriticScoreに直接現れない） |

3. **具体的な問題箇所を特定する:**
   - 問題のあるDayの日記テキスト（`output/day_XX.md`）を読む
   - 何が問題か（具体的な文章・表現・構造）を言語化する

---

## ステップ 2: 作業記録の開始

1. `.steering/[YYYYMMDD]-tune-[対象プロンプト名]/` ディレクトリを作成する
2. `requirement.md` に以下を記述する:
   - **問題:** 具体的にどのDayのどの部分が問題か
   - **原因分析:** なぜこの問題が発生しているか（プロンプトのどの指示が不十分か）
   - **改善目標:** 何をどの程度改善したいか
3. `design.md` にプロンプト変更の方針を記述する

---

## ステップ 3: 現在のプロンプトの分析

1. **対象プロンプトファイルを読み込む:**
   - `prompts/System_Persona.md`
   - `prompts/Prompt_StateUpdate.md`
   - `prompts/Prompt_Generator.md`
   - `prompts/Prompt_Critic.md`

2. **以下の観点で分析する:**
   - 指示が曖昧すぎる箇所はないか
   - 指示が矛盾している箇所はないか
   - 具体例（Few-shot）が不足していないか
   - `glossary.md` の用語と表現が一致しているか
   - ペルソナの禁則事項が明確に記述されているか

---

## ステップ 4: プロンプトの修正

1. **ブランチを作成する:**
   ```bash
   git checkout -b prompt/tune-[対象]
   ```

2. **修正の原則:**
   - **一度に1つの変更だけ行う。** 複数の変更を同時に行うと、効果の測定ができない
   - **具体的な指示に変更する。** 「良い文章を書いて」→「壮大な比喩を1段落に最低1つ含めて」
   - **具体例（Few-shot）を追加する。** LLMは抽象的な指示より具体例から学ぶ
   - **否定形より肯定形で書く。** 「〜しないで」→「〜してください」
   - **プレースホルダ名はコードと一致させる**

3. **修正パターン:**

   **temporal_consistency が低い場合:**
   - `Prompt_StateUpdate.md` に「memory_buffer の内容を必ず参照し、過去の出来事との接続を明示すること」を追加
   - `Prompt_Generator.md` に「過去の出来事を自然に回想する文を含めること」を追加

   **emotional_plausibility が低い場合:**
   - `Prompt_StateUpdate.md` に「emotional_impact の値に比例した感情変化を反映すること。-0.9のイベントでは stress が大きく上昇する」を追加
   - EMOTION_SENSITIVITY の具体的な計算式をプロンプトに明示することを検討

   **persona_deviation が低い場合:**
   - `System_Persona.md` の禁則事項をより具体的にする（悪い例を追加）
   - `Prompt_Generator.md` に文体ルールの具体的な適用例を追加

   **Critic の評価が偏る場合:**
   - `Prompt_Critic.md` の採点基準（1〜5の各スコア定義）をより具体的にする
   - 「3は合格ライン」であることを明示する
   - 各スコアの具体的な Pass/Reject 例を追加

---

## ステップ 5: 変更の検証

1. **問題のあったDayのみ再生成する:**
   ```bash
   python -m csdg.main --day [対象Day]
   ```

2. **CriticScore を確認する:**
   - 問題のあった評価軸のスコアが改善されたか
   - 他の評価軸のスコアが悪化していないか

3. **日記テキストの品質を確認する:**
   - 問題箇所が改善されたか
   - 新たな問題が発生していないか
   - ペルソナの禁則事項が維持されているか

4. **全Day実行で他への影響を確認する:**
   ```bash
   python -m csdg.main
   ```

5. **`log-analyzer` サブエージェントで全体の品質を再分析する**

---

## ステップ 6: 結果の記録

1. `.steering/` の `decisions.md` に以下を記録する:
   - **変更内容:** プロンプトのどの部分をどう変更したか
   - **変更前のスコア:** 問題のDayの CriticScore
   - **変更後のスコア:** 再生成後の CriticScore
   - **効果判定:** 改善/悪化/変化なし
   - **採用/却下:** この変更を採用するか

2. 効果がない、または悪化した場合:
   - 変更を revert する
   - 別のアプローチを検討する（Step 4 に戻る）

---

## ステップ 7: コミット

効果が確認された場合:

```bash
git add prompts/
git commit -m "prompt([対象]): [変更内容の要約]

- Day X の [評価軸] スコアが X → X に改善
- [具体的な変更内容]"
```

---

## チェックリスト（完了前の最終確認）

- [ ] 問題の原因を `log-analyzer` で特定した
- [ ] 一度に1つの変更のみ行った
- [ ] `glossary.md` の用語と一致している
- [ ] ペルソナの禁則事項が維持されている
- [ ] プレースホルダ名がコードと一致している
- [ ] 問題のDayでスコアが改善された
- [ ] 他のDayでスコアが悪化していない
- [ ] `.steering/decisions.md` に変更前後のスコアを記録した
- [ ] プロンプトファイル以外のコード変更を含んでいない
