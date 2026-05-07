# Design — critic-verdict

## アプローチ

`CriticScore` に **`verdict` フィールドを追加** し、`model_validator(mode="after")` で **常に再導出** する。`judge()` を `verdict == "pass"` 主導に書き換え、Pipeline は新たに `soft_fail` (= score≥3 + reject_reason 非空) を Reject 扱いとして retry させる。

### verdict 導出ルール (3 ケース)

| ケース | 既存 score | reject_reason | 既存 validator 結果 | 新 verdict |
|---|---|---|---|---|
| pass | 全 ≥ 3 | None | OK | `"pass"` |
| **soft_fail** (バグ実例) | 全 ≥ 3 | 非空 | OK (reject_reason 必須は score<3 のみ強制) | **`"soft_fail"`** |
| hard_fail | いずれか < 3 | 非空 (必須) | OK | `"hard_fail"` |
| 既存エラー | いずれか < 3 | None | ValidationError | (到達せず) |

### Validator 順序の決定 (Pydantic v2)

複数の `@model_validator(mode="after")` は **宣言順に実行される**。
- 既存 `check_reject_fields` を **先に** 残す → score<3 + reject_reason 欠落の既存 ValidationError 挙動を維持
- 新 `derive_verdict` を **後に** 配置 → 既存 validator を通過した有効な instance に対してのみ verdict を確定

LLM が `verdict` を直接出力しても (Structured Outputs schema に含まれる)、validator が常に上書きする → **真実源は score + reject_reason**。

## 検討した代替案

| 案 | 採否 | 理由 |
|---|---|---|
| 案 A: 新フィールド `verdict` 追加 + `model_validator(mode="after")` で自動導出 | **採用** | 後方互換 (default="pass")、CLAUDE.md 制約遵守、Pydantic 真実源化 |
| 案 B: `reject_reason` を `Optional` から `None` 強制 (score≥3 時) | 不採用 | 破壊的、CLAUDE.md「schemas.py 破壊的変更禁止」抵触、Critic LLM の自然な出力を捨てる |
| 案 C: `judge()` だけ書き換え (schemas.py そのまま) | 不採用 | 真実源が二重化 (judge 関数 vs schemas)。テストもロジック検証になり脆い |
| 案 D: Enum クラスで verdict を定義 | 不採用 | `Literal[...]` のほうが軽量・JSON schema 直接、Pydantic 推奨パターン |

## 変更ファイル一覧

| ファイル | 変更内容 | 影響範囲 |
|---|---|---|
| `csdg/schemas.py` | `Literal` import / `CriticScore.verdict` 追加 (default="pass") / `derive_verdict` validator 追加 | 全 Critic 利用箇所 (default あるため新規パラメータ不要) |
| `csdg/engine/critic.py` | `judge()` を `score.verdict == "pass"` に書き換え (1 箇所のみ) | Pipeline の Pass/Reject 判定 |
| `csdg/engine/pipeline.py:1212-1220` | soft_fail で `reject_reason` のみ populate されたケースを retry feedback に流す elif 追加 | リトライ品質 |
| `tests/test_schemas.py` | TestCriticScoreVerdict クラス新設 (pass/soft_fail/hard_fail/override) | 約 60 行追加 |
| `tests/test_critic.py` | judge() の verdict 駆動テスト (パラメタライズ) | 約 30 行追加 |
| `tests/test_pipeline.py` | TestSoftFailRetry クラス新設 (soft_fail がリトライ起動 + reject_reason フィードバック流入) | 約 50 行追加 |
| `docs/architecture.md` | §3.3 Critic に verdict 概念を追記 | 1 段落 |

## データフロー / インターフェース変更

### `schemas.py` のスキーマ変更詳細

```python
from typing import Literal

class CriticScore(BaseModel):
    # 既存フィールド (順序保持)
    temporal_consistency: int
    emotional_plausibility: int
    persona_deviation: int
    hook_strength: float = Field(default=0.0, ge=0.0, le=1.0, ...)
    reject_reason: str | None = Field(default=None, ...)
    revision_instruction: str | None = Field(default=None, ...)
    # 新規 (default あり、後方互換)
    verdict: Literal["pass", "soft_fail", "hard_fail"] = Field(
        default="pass",
        description="判定 (validator が score + reject_reason から自動導出)",
    )

    @field_validator("temporal_consistency", "emotional_plausibility", "persona_deviation")
    # ... 既存

    @model_validator(mode="after")
    def check_reject_fields(self) -> CriticScore:
        # ... 既存 (変更なし)

    @model_validator(mode="after")
    def derive_verdict(self) -> CriticScore:
        """verdict を score + reject_reason から再導出 (LLM 直出し値より優先)。"""
        is_hard = any(getattr(self, f) < 3 for f in ("temporal_consistency", "emotional_plausibility", "persona_deviation"))
        if is_hard:
            self.verdict = "hard_fail"
        elif self.reject_reason:
            self.verdict = "soft_fail"
        else:
            self.verdict = "pass"
        return self
```

### `critic.py:judge()` の変更

```python
def judge(score: CriticScore) -> bool:
    """verdict が pass のときのみ True (Pass)。soft_fail / hard_fail はリトライ対象。"""
    return score.verdict == "pass"
```

### `pipeline.py` のフィードバック合流変更 (1212-1220 付近)

```python
revision_parts: list[str] = []
if critic_score.revision_instruction:
    revision_parts.append(critic_score.revision_instruction)
elif critic_score.reject_reason:
    # soft_fail で revision_instruction 未populate のケースを救う
    revision_parts.append(critic_score.reject_reason)
if structural_violations:
    ...  # 既存
```

### Structured Outputs (Anthropic API) との整合性

- Pydantic v2 が JSON schema を生成 → `verdict` は `default="pass"` を持つため `required` には含まれない (Pydantic の標準挙動)
- LLM が verdict を出力しても validator が上書き → 真実源は score + reject_reason
- 既存 `prompts/Prompt_Critic.md` は変更不要 (LLM が verdict を理解しなくても問題なし)

## リスク / トレードオフ

### 既存テストへの影響

| 既存テスト | 影響 | 対応 |
|---|---|---|
| `tests/test_schemas.py::TestCriticScoreRejectValidation` | `_make_critic_score` のデフォルトはスコア 4/4/4 → verdict="pass" 自動付与。pass 系テストは無影響 | 変更不要 |
| Reject 系テスト (`test_reject_with_both_fields` 等) | score<3 + reject_reason 必須は既存 validator で維持 → verdict="hard_fail" 自動付与 | 変更不要 |
| `tests/test_pipeline.py::test_reject_then_pass_on_retry` | `_make_reject_score` (score=2 + reject_reason) → verdict="hard_fail"、judge() は False を返す → 既存挙動維持 | 変更不要 |
| Roundtrip テスト | verdict は default="pass" で serialize/deserialize 往復可能 | 変更不要 |

### Pydantic v2 validator order

`@model_validator(mode="after")` は **クラス内の宣言順** で実行される。`check_reject_fields` を先、`derive_verdict` を後にすれば安全。decisions.md に記録予定。

### 後方互換性

- Critic LLM の既存出力 (verdict なし) → default="pass" + validator 自動上書きで吸収
- 既存 generation_log.json (verdict なし) の deserialize → default="pass" で復元、ただし verdict は再計算されないので元データに verdict が無いまま (検証不要、ログは observation only)

### パフォーマンス

- validator 1 個追加につき per-instance O(3) → 無視できる

### 行動変化 (重要)

soft_fail を Reject 扱いにすることで、**過去 Pass だったケースが Reject** になり API 呼び出しが増える可能性がある。実運用での効果測定のため `output/generation_log.json` の retry_count 分布を実装後に監視 (decisions.md に記録)。

## 未確定事項 → 確定済み

- ✓ `CriticScore` インスタンス化箇所: `csdg/engine/critic.py:937-944` のみ + テスト 2 箇所
- ✓ `judge()` 呼び出し元: `csdg/engine/pipeline.py:1132` の 1 箇所のみ
- ✓ Pipeline 側の reject_reason フィードバック統合: 既存 revision_parts に elif でフォールバック追加 (5 行)
