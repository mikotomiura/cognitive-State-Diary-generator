# .steering — 構造化作業ノート

各作業セッションでの記録を蓄積するディレクトリ。

## ディレクトリ構造

```
.steering/
├── README.md                  # このファイル
├── _setup-progress.md         # Claude Code 環境構築フェーズの進捗
├── _verify-report-*.md        # /verify-setup の出力
├── _template/                 # タスク用テンプレート
│   ├── requirement.md
│   ├── design.md
│   ├── tasklist.md
│   ├── blockers.md (任意)
│   └── decisions.md (任意)
└── [YYYYMMDD]-[タスク名]/      # 実タスクの作業ノート
    ├── requirement.md
    ├── design.md
    ├── tasklist.md
    └── ...
```

## 命名規約

- ディレクトリ: `[YYYYMMDD]-[kebab-case-task-name]/` (例: `20260507-codex-bridge/`)
- アンダースコア `_` で始まるファイル/ディレクトリは Setup / verify などのメタ情報用
- タスク作業中は requirement / design / tasklist の 3 ファイル必須、blockers / decisions は必要時のみ

## 運用フロー

1. `/start-task` でディレクトリ作成 + `_template/` から要件・設計・タスクリストを生成
2. 実装中、tasklist.md のチェックを進めながら作業
3. ブロッカーや重要決定が発生したら `blockers.md` / `decisions.md` を追加
4. `/finish-task` で最終化 + コミット
