---
name: pydantic-patterns
description: >
  CSDG プロジェクトにおける Pydantic v2 モデル設計のパターンとベストプラクティス。
  schemas.py のモデル追加・変更時、Structured Outputs のスキーマ設計時、
  バリデーションロジックの実装時に参照する。
  Field 定義、field_validator、model_config、シリアライズ、
  Structured Outputs 対応を包括的にカバーする。
allowed-tools: Read, Grep, Glob
---

# Pydantic モデル設計パターン

## 基本原則

1. **すべてのフィールドに `Field(description=...)` を付ける** — Structured Outputs のスキーマ記述に使用される
2. **バリデーションは `field_validator` で宣言的に記述する** — 手続き的な外部チェックを書かない
3. **ミュータブルデフォルトには `default_factory` を使う** — `list`, `dict` のデフォルトは `Field(default_factory=list)`
4. **連続変数は必ずクランプする** — `-1.0` 〜 `1.0` の範囲を保証する
5. **モデル変更は影響範囲が広い** — 変更時は `impact-analyzer` で影響範囲を確認する

---

## CSDG のモデル一覧

| モデル | 用途 | Structured Outputs |
|---|---|---|
| `DailyEvent` | シナリオ入力 | 不要（コード内で定義） |
| `CharacterState` | Actor出力 (Phase 1) | **必要** |
| `CriticScore` | Critic出力 (Phase 3) | **必要** |
| `GenerationRecord` | ログ記録 | 不要（内部使用） |
| `PipelineLog` | ログ全体 | 不要（内部使用） |

Structured Outputs で使用するモデルは、LLM が生成する JSON の構造を定義するため、`description` の品質がLLMの出力品質に直結する。

---

## モデル定義の標準パターン

```python
from pydantic import BaseModel, Field, field_validator

class CharacterState(BaseModel):
    """キャラクター内部状態 (h_t)。"""

    # --- 連続変数 ---
    fatigue: float = Field(description="疲労度 (-1.0: 絶好調 〜 1.0: 限界)")
    motivation: float = Field(description="モチベーション (-1.0: 虚無 〜 1.0: やる気満々)")
    stress: float = Field(description="ストレス値 (-1.0: リラックス 〜 1.0: 爆発寸前)")

    # --- 離散変数 ---
    current_focus: str = Field(description="現在最も関心を持っている事柄")
    unresolved_issue: str | None = Field(default=None, description="未解決の悩みや課題")
    growth_theme: str = Field(description="1週間を通じた成長テーマ")

    # --- 累積記憶 ---
    memory_buffer: list[str] = Field(default_factory=list, description="過去3日分のdaily_summary")
    relationships: dict[str, float] = Field(default_factory=dict, description="人物への好感度")

    @field_validator("fatigue", "motivation", "stress")
    @classmethod
    def clamp_continuous(cls, v: float) -> float:
        """連続変数を -1.0〜1.0 にクランプする。"""
        return max(-1.0, min(1.0, v))

    @field_validator("memory_buffer")
    @classmethod
    def limit_buffer(cls, v: list[str]) -> list[str]:
        """memory_buffer を最大3件に制限する。"""
        return v[-3:] if len(v) > 3 else v
```

---

## 補足資料

- `examples.md` — モデル定義・バリデーション・シリアライズの実装例集
- `validation-recipes.md` — よくあるバリデーションパターンのレシピ集
