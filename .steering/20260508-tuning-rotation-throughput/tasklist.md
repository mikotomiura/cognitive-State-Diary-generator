# Tasklist — tuning-rotation-throughput

## 実装

- [x] `scripts/throughput_report.py` 新規追加（4 ラン分析対応）
- [x] `tests/test_throughput_report.py` 新規追加（20 件、AAA + パラメタライズ）
- [x] `.steering/20260508-tuning-rotation-throughput/findings.md` 報告書作成
- [x] `csdg/` / `prompts/` / `schemas.py` への変更なし（破壊禁止ルール遵守）

## 検証

- [x] `pytest tests/test_throughput_report.py -v` 緑（20 件 Pass）
- [x] `pytest tests/ -m "not e2e"` 緑（551 件 Pass、リグレッションなし）
- [x] `mypy scripts/throughput_report.py tests/test_throughput_report.py --strict` 通過
- [x] `ruff check scripts/throughput_report.py tests/test_throughput_report.py` 通過
- [x] `ruff format --check scripts/throughput_report.py tests/test_throughput_report.py` 通過
- [x] 4 ランすべてで `python scripts/throughput_report.py` が正常出力（findings.md 9 章参照）

## 主な発見（findings.md 詳細）

- [x] Phase 2 (Content Generation) が時間の 56-59% (平均 57%) を占める → 主ボトルネック
- [x] 6 プロンプト中 5 つが全 run で同一ハッシュ → LLM レスポンスキャッシュの効果余地大
- [x] retry のスコア lift は改善 5 / 同点 3 / 悪化 5 → Critic フィードバック連鎖は期待ほど機能していない

## 採用案（findings.md §6 の推奨順）

- [x] **1st**: LLM レスポンスキャッシュ → 後続タスク `feat/llm-response-cache`
- [x] **2nd**: `--day N` 強化 + state 復元 → 後続タスク `feat/day-resume-from-cache`
- [x] **3rd**: 固定 seed / temp=0 モード → 後続タスク `feat/deterministic-eval-mode`
- [x] Best-of-N 並列化はペンディング（前タスク `20260507-best-of-n-parallel` のメモを保持）

## 仕上げ

- [x] requirement.md 最終化
- [x] design.md 最終化
- [x] findings.md 作成・採用案決定
- [x] code-reviewer によるレビュー（HIGH/MEDIUM 指摘を反映）
  - H-01: `_records` → `_get_records`、`_executed_at` → `_get_executed_at` (quality_report.py と命名統一)
  - H-02: private 関数の直接 import は意図的判断として `decisions.md` D-01 に記録
  - M-01: `Any` 使用箇所にコメント追加
  - M-02: テスト fixture のハッシュ値を SHA256 (64 文字) 模擬に変更
  - L-03: `generate_report` の docstring に Args/Returns/Self-Healing 説明を追記
- [x] decisions.md 作成（D-01: テスト方針 / D-02: 採用案優先順位）
- [ ] `/finish-task` 実行（コミット）
