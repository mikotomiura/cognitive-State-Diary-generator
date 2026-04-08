# /add-scenario — シナリオ追加ワークフロー

> **目的:** 新しい DailyEvent をシナリオに追加する、または既存のシナリオを変更する際のワークフロー。
> **粒度:** 1つのシナリオ変更（Dayの追加、イベントの変更、初期状態の調整）。

---

## ステップ 1: シナリオ設計の確認

1. **既存シナリオの確認:**
   - `csdg/scenario.py` を読み、現在の7日分の `DailyEvent` 定義を確認する
   - `docs/functional-design.md` のシナリオ仕様セクション（§8）を読み、物語アーク構造を確認する

2. **物語アークとの整合性を検討する:**
   ```
   Day 1-2: 日常（導入・対比の確立）
   Day 3:   摩擦（衝突）
   Day 4:   転機（発狂・イデオロギーへの反発）→ emotional_impact: -0.9
   Day 5-6: 揺らぎ（回復と接続）
   Day 7:   着地（問いとしての着地）
   ```

3. **キャラクター設定の確認:**
   - `docs/glossary.md` のキャラクター用語セクションを確認する
   - ペルソナの禁則事項を確認する
   - 人物関係（深森那由他、ミナ）を確認する

---

## ステップ 2: イベントの設計

新しい `DailyEvent` を設計する。以下のフィールドをすべて定義する:

| フィールド | 制約 | 設計のポイント |
|---|---|---|
| `day` | 1〜の連番整数 | 既存のDay番号との連続性を維持する |
| `event_type` | `positive` / `negative` / `neutral` | 物語アーク上の役割に合わせる |
| `domain` | 空文字列でないこと | `仕事` / `人間関係` / `趣味` / `内省` / `思想` |
| `description` | 10文字以上 | 客観的な出来事の記述。キャラクターの感情は含めない |
| `emotional_impact` | -1.0 〜 +1.0 | 物語上の重要度に応じて設定する |

**設計上の注意:**
- `emotional_impact` の絶対値が `0.7` を超えるイベントは、システムのストレステストとして機能する。リトライが発生する可能性が高くなることを考慮する
- `description` はキャラクターの感情を含めず、客観的事実のみを記述する。感情はActorが生成する
- 新しい人物を登場させる場合は、`CharacterState.relationships` の初期値と `System_Persona.md` にも追加が必要

---

## ステップ 3: 感情パラメータの想定推移

新しいイベントを含めた全Day分の感情パラメータ想定推移テーブルを作成する:

```markdown
| Day | event_type | emotional_impact | stress想定 | motivation想定 | 物語上の役割 |
|---|---|---|---|---|---|
| X | (type) | (impact) | (想定値) | (想定値) | (役割) |
```

**`expected_delta` の計算:**
```
stress_delta    = emotional_impact × (-0.3)
motivation_delta = emotional_impact × 0.4
fatigue_delta   = emotional_impact × (-0.2)
```

想定推移が物語アークの意図と一致していることを確認する。

---

## ステップ 4: バリデーション

以下のバリデーションルールを満たしているか確認する:

- [ ] `day` フィールドが1から連番であること（欠番なし）
- [ ] `event_type` が `positive` / `negative` / `neutral` のいずれかであること
- [ ] `domain` が空文字列でないこと
- [ ] `description` が10文字以上であること
- [ ] `emotional_impact` が -1.0 〜 +1.0 の範囲内であること
- [ ] 物語アークの「日常→転機→揺らぎ→着地」構造が維持されていること
- [ ] 新しい人物を登場させる場合、`relationships` に追加したこと

---

## ステップ 5: 実装

1. `csdg/scenario.py` にイベントを追加/変更する
2. 初期状態 `h_0` の調整が必要であれば更新する
3. テストを実行する:
   ```bash
   pytest tests/test_scenario.py -v
   ```

---

## ステップ 6: 検証実行

1. 変更したDayのみパイプラインを試行する:
   ```bash
   python -m csdg.main --day [対象Day]
   ```
2. CriticScore が合格基準を満たすか確認する
3. 前後のDayとの整合性に問題がないか確認する
4. 問題がある場合は、イベントの `emotional_impact` や `description` を調整する

---

## ステップ 7: ドキュメント更新

1. `docs/functional-design.md` のシナリオ仕様セクション（§8）を更新する
2. 感情パラメータ想定推移テーブルを更新する
3. 新しいDay固有のストレステスト仕様があれば追加する

---

## チェックリスト

- [ ] DailyEvent のバリデーションルールをすべて満たしている
- [ ] 物語アークの構造が維持されている
- [ ] expected_delta を計算し、想定推移が妥当
- [ ] `test_scenario.py` が Pass している
- [ ] パイプライン試行で CriticScore が合格基準を満たした
- [ ] `functional-design.md` のシナリオ仕様を更新した
