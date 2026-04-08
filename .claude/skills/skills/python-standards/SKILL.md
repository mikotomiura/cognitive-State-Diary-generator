---
name: python-standards
description: >
  CSDG プロジェクトにおける Python コーディング規約とベストプラクティス。
  新しい Python コードを書く際、既存コードをレビューする際、
  リファクタリングを行う際に参照する。
  型アノテーション、docstring、エラーハンドリング、ロギング、
  非同期処理、import 規約を包括的にカバーする。
allowed-tools: Read, Grep, Glob, Bash
---

# Python コーディング規約

## 基本設定

- **Python バージョン:** 3.11 以上
- **最大行長:** 120文字
- **リンター:** ruff（flake8 + isort + black 統合）
- **型チェック:** mypy strict mode
- **フォーマッター:** ruff format

---

## 型アノテーション

### 必須ルール

すべての関数・メソッドに型アノテーションを付ける。例外なし。

```python
# ✅ 正しい
def compute_deviation(prev: CharacterState, curr: CharacterState) -> dict[str, float]:
    ...

# ❌ 型アノテーションなし
def compute_deviation(prev, curr):
    ...
```

### 推奨パターン

```python
# Union 型は | 構文を使う (Python 3.10+)
def get_issue(state: CharacterState) -> str | None:
    return state.unresolved_issue

# コレクション型はジェネリクスを使う
def get_memories(buffer: list[str]) -> list[str]:
    return buffer[-3:]

# 複雑な型にはエイリアスを定義する
from typing import TypeAlias
EmotionMap: TypeAlias = dict[str, float]

# コールバック型
from collections.abc import Callable
RetryStrategy: TypeAlias = Callable[[int], float]  # attempt -> temperature
```

### 禁止パターン

```python
# ❌ Any 型は原則禁止
from typing import Any
def process(data: Any) -> Any:  # 何が入って何が出るか分からない
    ...

# ❌ 古い Optional 構文
from typing import Optional
def get_issue(state: CharacterState) -> Optional[str]:  # X | None を使う
    ...
```

---

## docstring

Google style を使用する。詳細は `examples.md` を参照。

```python
def update_state(prev_state: CharacterState, event: DailyEvent) -> CharacterState:
    """イベントに基づきキャラクターの内部状態を更新する。

    Args:
        prev_state: 前日のキャラクター内部状態 (h_{t-1})。
        event: 当日のイベント定義 (x_t)。

    Returns:
        更新されたキャラクター内部状態 (h_t)。

    Raises:
        pydantic.ValidationError: LLM出力がスキーマに適合しない場合。
    """
```

---

## エラーハンドリング

- 裸の `except:` は禁止
- `except Exception` は最外周でのみ許可
- 例外の握りつぶし禁止
- `logging` で記録

詳細は `examples.md` と `anti-patterns.md` を参照。

---

## ロギング

`print()` 禁止。`logging` モジュールを使用する。

```python
import logging
logger = logging.getLogger(__name__)

logger.info("[Day %d] Phase 1: State Update ... OK (%.1fs)", day, elapsed)
logger.warning("バリデーションエラー (Day %d): %d errors", day, err_count)
```

---

## 非同期処理

LLM API 呼び出しを含む関数は `async` で定義する。

```python
async def generate_diary(self, state: CharacterState, event: DailyEvent) -> str:
    response = await self.client.generate_text(...)
    return response
```

---

## import 規約

ruff の isort 互換ルールに従う。順序: 標準ライブラリ → サードパーティ → ローカル。

```python
# 標準ライブラリ
import logging
from pathlib import Path

# サードパーティ
from pydantic import BaseModel, Field, field_validator

# ローカル
from csdg.config import CSDGConfig
from csdg.schemas import CharacterState, DailyEvent
```

---

## 補足資料

- `examples.md` — 正しい実装パターンのコード例集
- `anti-patterns.md` — 避けるべきアンチパターン集
