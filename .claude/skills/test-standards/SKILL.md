---
name: test-standards
description: >
  CSDG プロジェクトにおけるテスト設計・実装の基準とベストプラクティス。
  テストコードを書く際、テスト戦略を立てる際、
  テスト品質を評価する際に参照する。
  テスト分類、AAA パターン、モック戦略、パラメタライズ、
  フィクスチャ設計、カバレッジ目標を包括的にカバーする。
allowed-tools: Read, Grep, Glob, Bash
---

# テスト設計・実装基準

## テスト分類

| 分類 | 対象 | LLM API | 実行頻度 |
|---|---|---|---|
| 単体テスト | schemas, config, critic ロジック | 不要 | 常時 |
| モックテスト | actor, critic の LLM 呼び出し | モック | 常時 |
| 統合テスト | pipeline の正常系・異常系 | モック | 常時 |
| E2Eテスト | pipeline の実 API 呼び出し | 実 API | 手動のみ |

---

## テスト実装の原則

### AAA パターン（Arrange-Act-Assert）

```python
def test_clamp_upper_bound() -> None:
    """1.0を超える値は1.0にクランプされる。"""
    # Arrange: テストデータの準備
    raw_fatigue = 1.5

    # Act: テスト対象の実行
    state = CharacterState(
        fatigue=raw_fatigue, motivation=0.0, stress=0.0,
        current_focus="test", growth_theme="test",
    )

    # Assert: 結果の検証
    assert state.fatigue == 1.0
```

### 命名規約

- テストクラス: `Test` + テスト対象 + テスト観点
- テストメソッド: `test_` + テスト内容（スネークケース）
- docstring: 「何をテストしているか」を1行で

```python
class TestCharacterStateClamp:
    """CharacterState の連続変数クランプのテスト。"""

    def test_clamp_upper_bound(self) -> None:
        """1.0を超える値は1.0にクランプされる。"""

    def test_clamp_lower_bound(self) -> None:
        """-1.0未満の値は-1.0にクランプされる。"""

    def test_within_range_unchanged(self) -> None:
        """範囲内の値はそのまま保持される。"""
```

---

## カバレッジ目標

| モジュール | 目標 | 理由 |
|---|---|---|
| `schemas.py` | 95% | 全バリデーションの検証が必須 |
| `config.py` | 90% | 設定値の変換ロジック |
| `engine/critic.py`（ロジック） | 95% | 純粋関数でテスト容易 |
| `engine/actor.py` | 80% | LLMモック部分を含む |
| `engine/pipeline.py` | 85% | リトライ・フォールバック全パターン |
| `scenario.py` | 90% | バリデーションルール |
| `visualization.py` | 70% | グラフ生成の正常完了 |

---

## モック戦略

LLM API は必ずモックする（E2Eテスト以外）。

```python
from unittest.mock import AsyncMock
from csdg.engine.llm_client import LLMClient

@pytest.fixture
def mock_llm() -> LLMClient:
    client = AsyncMock(spec=LLMClient)
    client.generate_structured.return_value = CharacterState(...)
    client.generate_text.return_value = "日記テキスト"
    return client
```

**モックの原則:**
- `LLMClient` の抽象インターフェースに対してモックする
- テストケースごとにモックの戻り値を設定する
- 異常系テストでは `side_effect` で例外を発生させる

---

## 補足資料

- `examples.md` — テスト実装の具体的なコード例集
- `fixture-patterns.md` — フィクスチャ設計パターン集
