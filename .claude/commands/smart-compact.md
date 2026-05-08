---
description: >
  CSDG プロジェクトの構造 (.steering / CLAUDE.md / docs) を理解した上で、
  現セッションの重要決定・タスク状態・ファイルパスを handoff ファイルへ保存し、
  その後で Claude 標準 /compact を呼ぶか /clear で再開する判断材料を提示する。
  コンテキスト使用率が 60% を超えた時、長時間セッションで集中力が落ちた時、
  または別タスクへ切り替える前のセーブポイント作成時に起動する。
allowed-tools: Read, Write, Edit, Bash(git *), Bash(ls *), Bash(date *)
---

# /smart-compact

## 現在の状況
!`git status --short 2>/dev/null`

## アクティブタスク
!`ls -t .steering/ 2>/dev/null | grep -E '^[0-9]{8}-' | head -3`

## 直近のコミット
!`git log --oneline -5 2>/dev/null`

---

## 実行フロー

### Step 1: 現在のタスク識別

`.steering/` で最新タスクディレクトリを特定。
複数候補がある時 (modified files が複数タスクに分散) はユーザーに尋ねる。

### Step 2: handoff.md の生成

`.steering/[現在のタスク]/handoff.md` を Write で作成 (既存なら追記):

```markdown
# Handoff — [YYYY-MM-DD HH:MM]

## セッションの目的
[このセッションで何をしようとしていたか、1〜2 文]

## 完了した作業
- [ファイル変更や決定の bullet list、git diff --stat と git log を参考に]

## 進行中の作業 (中断ポイント)
- [現在編集中のファイル / 検証中のテスト / 検討中の設計]

## 重要な決定
- [このセッションで確定した設計判断、トレードオフ、採用 / 不採用案]
- → 詳細は decisions.md / design.md を参照

## 次セッションで再開する手順
1. [最初に Read すべきファイル]
2. [次に検討すべき論点]
3. [想定される次のコマンド: /implement / /review-changes / /finish-task など]

## 触ってはいけない / 注意事項
- [このセッションで判明した落とし穴、避けるべきアプローチ]

## 参考リンク
- design.md: [今回のタスクの設計]
- relevant docs: [docs/ 配下の参照すべきファイル]
- 関連コミット: [git log で抽出した hash]
```

各セクションの中身は **このセッションの実情** から抽出する。テンプレートをそのまま埋めてはいけない。

### Step 3: handoff の品質チェック

書き出した handoff.md を Read し直して、以下を満たすか確認:

- [ ] 「次セッションで再開する手順」が具体的 (ファイル名・行数・コマンド名が含まれる)
- [ ] 「重要な決定」が tasklist.md / decisions.md と矛盾していない
- [ ] 「進行中の作業」を読めば、どこで詰まっていたかが他人にも分かる

不足があれば追記してから次へ。

### Step 4: ユーザーへ次のアクション提示

handoff.md の内容を要約 (5〜10 行) してユーザーに見せた上で、選択肢を提示:

| 選択肢 | 用途 | 実行内容 |
|---|---|---|
| **/compact** | 同タスクを継続したい (会話履歴の要約圧縮で context 回復) | Claude 標準 `/compact` を起動。handoff.md は次セッションでも残る |
| **/clear** | 別タスクへ切り替える / 完全リフレッシュしたい | セッション履歴を破棄。次に `/start-task` か既存タスク再開 |
| **このまま続ける** | handoff だけ取って作業継続 (セーブポイントとしての利用) | 何もしない |

> /compact は会話履歴を summarize して context を縮める一方、auto-compact と異なり手動制御。
> /clear はファイル状態に影響しないが、agent やタスクの「記憶」が完全消失する。
> handoff.md は両者で生き残るので、本コマンドの本来の価値はこの handoff 生成にある。

### Step 5: 進捗の記録 (任意)

選択した行動を `.steering/[現在のタスク]/handoff.md` の末尾に追記:

```markdown
---
セッション終了アクション: /compact 実行 (YYYY-MM-DD HH:MM)
context 圧縮後の継続を予定
```

## 制約

- **handoff.md を空テンプレで保存しない** (このコマンドの存在意義が消える)
- **コミット未確定の変更を勝手に commit しない** (セーブポイント作成と commit は別レイヤ)
- **決定の根拠を省略しない** (将来の自分が判断を追跡できなくなる)
- **`/compact` や `/clear` を勝手に実行しない** (ユーザー承認後に推奨を提示するのみ)
- 動作対象は `.steering/[YYYYMMDD]-*` のアクティブタスク 1 つに限定

## アンチパターン

- handoff.md にツール出力の生ログを貼る (要約せよ)
- セッション開始からの全履歴を時系列で書き出す (再開に必要な情報だけに絞る)
- 「次にやること」が抽象的 (例: 「テストを直す」ではなく「`tests/test_pipeline.py:142` の TestBestOfN を pass させる」)
- 既存の design.md / decisions.md と重複させる (handoff は橋渡し、設計の真実源ではない)
