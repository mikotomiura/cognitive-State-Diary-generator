---
description: >
  ワークフロー型のスラッシュコマンド群を .claude/commands/ 配下に構築する。
  start-task, add-feature, fix-bug, refactor, review-changes, smart-compact,
  finish-task の 7 つのコマンドを 1 ファイルずつ承認を得ながら作成する。
  各コマンドは Phase 3-4 で作成された Skill と Agent を組み合わせて呼び出す。
  /setup-agents の完了後に実行する。
allowed-tools: Read, Write, Glob, Bash(mkdir *), Bash(ls *)
---

# /setup-commands — スラッシュコマンド群構築コマンド

> Phase 5 of 7. Let's think step by step.

## 環境チェックブロック

### Check 1: 進捗ファイル

```bash
cat .steering/_setup-progress.md
```

Phase 4 完了を確認。

### Check 2: Skill と Agent の存在

```bash
ls .claude/skills/
ls .claude/agents/
```

両方が存在することを確認。Commands はこれらを呼び出す。

### Check 3: コンテキスト予算

`/context` で 30% 以下を確認。

## 設計原則

### 1. 単一責任の原則

1 つのコマンドは 1 つの目的に集中。`/develop-application` のような巨大コマンドは作らない。

### 2. 適切な粒度

「1 回の作業セッションで完了する一連の手順」が目安。

### 3. 明確な実行フロー

各ステップで何をするか、どのツールを使うかを具体的に記述。抽象的な指示は避ける。

### 4. Skill と Agent の積極的活用

メインエージェントが直接全部やるのではなく、専門の Skill と Agent に委譲する。

## 実行フロー

### Step 1: 既存 Skill と Agent の把握

`.claude/skills/` と `.claude/agents/` 配下のファイルを Glob で確認。各 Skill と Agent の name を頭に入れる。

### Step 2: ディレクトリ作成

```bash
ls .claude/commands/
```

`/bootstrap` で既に作成されているはず。なければ作成:

```bash
mkdir -p .claude/commands
```

### Step 3: 7 つのコマンドを 1 つずつ作成

> **重要**: 必ず 1 つずつ作成し、各コマンド完成後に **(a) ユーザー承認** + **(b) Grill me ステップ** を実施。

順序: `/start-task` → `/add-feature` → `/fix-bug` → `/refactor` → `/review-changes` → `/smart-compact` → `/finish-task`

#### 3.1 `/start-task`

```markdown
---
description: >
  新規タスクの作業を開始する。.steering/[YYYYMMDD]-[task-name]/ を作成し、
  requirement.md, design.md, tasklist.md のテンプレートを配置して
  初期ヒアリングを行う。実装作業を始める前に必ず最初に実行する。
allowed-tools: Write, Bash(mkdir *), Bash(date *), Bash(cp *), Read
---

# /start-task

## 目的

新規タスクの開始時に作業記録ディレクトリを作成し、必須ファイルを配置して初期要件を記録する。

## 実行フロー

### Step 1: タスク名の取得

ユーザーにタスク名を尋ねる:

> 「これから始めるタスクの名前を教えてください。kebab-case で 5-30 文字程度を推奨します。例: `add-user-authentication`, `fix-login-bug`」

### Step 2: 日付の取得

\`\`\`bash
date +%Y%m%d
\`\`\`

### Step 3: ディレクトリ作成

\`\`\`bash
mkdir -p .steering/[YYYYMMDD]-[task-name]
\`\`\`

### Step 4: テンプレートのコピー

\`\`\`bash
cp .steering/_template/requirement.md .steering/[YYYYMMDD]-[task-name]/
cp .steering/_template/design.md .steering/[YYYYMMDD]-[task-name]/
cp .steering/_template/tasklist.md .steering/[YYYYMMDD]-[task-name]/
\`\`\`

### Step 5: requirement.md の初期記入

ユーザーに以下を順番に質問（一度に複数質問しない）:

1. このタスクの背景は何ですか?
2. ゴール（完了条件）は何ですか?
3. スコープに含まれるものは?
4. スコープに含まれないものは?
5. 受け入れ条件をリストで挙げてください

回答を requirement.md に Edit ツールで記入する。

### Step 6: タスクの種類の判定

ユーザーに尋ねる:

> 「このタスクは以下のどれに該当しますか?
> 1. 新機能追加 → 次に `/add-feature` を実行
> 2. バグ修正 → 次に `/fix-bug` を実行
> 3. リファクタリング → 次に `/refactor` を実行
> 4. その他」

### Step 7: 完了通知

\`\`\`
タスク `.steering/[YYYYMMDD]-[task-name]/` を作成しました。

作成ファイル:
- requirement.md (記入済み)
- design.md (空)
- tasklist.md (空)

次のステップ: 上記で選択したコマンド (`/add-feature` / `/fix-bug` / `/refactor`) を実行してください。
\`\`\`

## 制約

- ヒアリングを省略しない
- requirement.md の記入を省略しない
- 一度に複数の質問をしない
```

ユーザー承認 + Grill me。

#### 3.2 `/add-feature`

```markdown
---
description: >
  新機能追加の完全なワークフロー。プロジェクト理解から実装、テスト、
  レビュー、ドキュメント更新まで一連の手順を実行する。
  /start-task で作業ディレクトリを作成した後に実行する。
  file-finder, impact-analyzer, code-reviewer, test-runner などの
  サブエージェントを段階的に呼び出す。
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(git *), Task
---

# /add-feature

## 目的

新機能を追加する際の標準ワークフローを実行する。

## 前提条件

- [ ] `/start-task` で `.steering/[YYYYMMDD]-[task-name]/` が作成済み
- [ ] requirement.md に要件が記入済み

## 実行フロー

### Step 1: プロジェクト理解

以下のドキュメントを Read で読む:

1. `CLAUDE.md`
2. `docs/architecture.md`
3. `docs/development-guidelines.md`
4. `docs/repository-structure.md`
5. `.steering/[現在のタスク]/requirement.md`

### Step 2: 既存パターンの調査

`file-finder` サブエージェントを起動:

> Task: file-finder で「[機能名] に類似する既存実装」を検索。類似機能の実装場所と、参考にすべきパターンを報告してください。

`impact-analyzer` サブエージェントを起動:

> Task: impact-analyzer で「[追加する機能] の実装による影響範囲」を分析。影響を受けるファイル、テスト、ドキュメントをリストアップしてください。

### Step 3: 設計

調査結果をもとに `.steering/[現在のタスク]/design.md` を記入:

- 実装アプローチ
- 変更対象ファイル
- 新規作成ファイル
- 既存パターンとの整合性
- テスト戦略

ユーザーに設計の承認を求める:

> 「設計案を design.md に記入しました。確認していただけますか?」

ユーザー承認後に次へ。

### Step 4: tasklist の作成

`.steering/[現在のタスク]/tasklist.md` に具体的なタスクを列挙する。
チェックボックス形式で。各タスクは 30 分以内で完了できる粒度に。

### Step 5: 実装

tasklist の各項目を順番に実装する。各タスク完了ごとに:

1. tasklist のチェックボックスを Edit で更新
2. 関連 Skill を必要に応じて参照（test-standards, [language]-standards など）

実装中は適宜 `/context` で予算を確認。50% を超えたら一度区切って `/smart-compact`。

### Step 6: テストと検証

`test-runner` サブエージェントを起動:

> Task: test-runner で関連テストを実行。

失敗があれば `test-analyzer` を起動:

> Task: test-analyzer で失敗の原因を分析。

修正してテストを再実行。すべて通るまで繰り返す。

### Step 7: コードレビュー

`code-reviewer` サブエージェントを起動:

> Task: code-reviewer で変更内容をレビュー。HIGH/MEDIUM の指摘を中心に報告してください。

HIGH の指摘があればすべて対応する。MEDIUM はユーザーに対応するか確認。

### Step 8: セキュリティチェック（外部入力を扱う場合）

新機能が外部入力（ユーザー入力、API、ファイルアップロードなど）を扱う場合、`security-checker` を起動:

> Task: security-checker でセキュリティリスクを調査。

CRITICAL/HIGH があれば必ず対応。

### Step 9: ドキュメント更新

以下のドキュメントを必要に応じて更新:
- `docs/functional-design.md`（新機能の追加）
- `docs/glossary.md`（新用語の追加）
- `docs/architecture.md`（アーキテクチャに影響する変更）

### Step 10: 完了処理

ユーザーに通知:

> 「実装が完了しました。`/finish-task` を実行して作業を完了してください。」

## 制約

- Step 3 の設計承認を得ずに Step 5 に進まない
- Step 6 のテストが失敗したまま Step 7 に進まない
- Step 7 の HIGH 指摘を放置しない
- 各サブエージェント呼び出し時、用途と期待する出力を明確に指定する
```

ユーザー承認 + Grill me。

#### 3.3 `/fix-bug`

```markdown
---
description: >
  バグ修正の完全なワークフロー。再現確認、原因特定、修正、回帰テストまで実行する。
  /start-task で作業ディレクトリを作成した後に実行する。
  file-finder, log-analyzer, impact-analyzer, test-runner などを使う。
allowed-tools: Read, Edit, Glob, Grep, Bash(git *), Task
---

# /fix-bug

## 実行フロー

### Step 1: バグの再現と理解

ユーザーから以下を聞く（一度に複数質問しない）:
- 再現手順
- 期待される動作
- 実際の動作
- エラーメッセージ（あれば）
- 発生環境

これらを `.steering/[現在のタスク]/requirement.md` に Edit で追記。

### Step 2: 関連コードの特定

`file-finder` サブエージェントを起動:

> Task: file-finder で「[バグの症状] に関連するファイル」を検索。

### Step 3: ログの確認（必要に応じて）

ログがある場合、`log-analyzer` サブエージェントを起動:

> Task: log-analyzer で関連するログを分析。

### Step 4: 原因の特定

関連コードを Read で読み、原因を特定する。

特定した原因を `.steering/[現在のタスク]/design.md` に記録:

\`\`\`markdown
## バグの原因
[詳細な分析]

## 根本原因
[原因の本質]

## 修正方針
[どう直すか]
\`\`\`

### Step 5: 影響範囲の確認

`impact-analyzer` を起動:

> Task: impact-analyzer で修正の影響範囲を分析。

### Step 6: 回帰テストの追加（TDD アプローチ推奨）

このバグが再発しないようなテストケースを **修正前に** 追加する。
このテストは現時点では失敗するはず。

### Step 7: 修正の実装

最小限の変更で修正する。広範囲のリファクタリングは別タスクにする。

### Step 8: テスト実行

`test-runner` サブエージェントを起動:

> Task: test-runner でテストを実行。Step 6 で追加したテストを含む全テストを実行。

すべて通るまで修正を続ける。

### Step 9: コードレビュー

`code-reviewer` を起動:

> Task: code-reviewer で修正内容をレビュー。

### Step 10: blockers.md の作成（任意）

このバグのデバッグで困った点があれば、`.steering/[現在のタスク]/blockers.md` に記録。次回似た問題に遭遇した時の参考になる。

### Step 11: 完了処理

`/finish-task` を実行する。

## 制約

- 原因が特定できないまま修正しない
- 回帰テストを追加せずに修正に入らない
- 影響範囲を確認せずにマージしない
- 「とりあえず動いた」で終わらせない
```

ユーザー承認 + Grill me。

#### 3.4 `/refactor`

```markdown
---
description: >
  リファクタリングの完全なワークフロー。既存テストの確認、影響範囲分析、
  段階的な変更、テスト維持を実行する。振る舞いを変えない変更だけを扱う。
allowed-tools: Read, Edit, Glob, Grep, Bash(git *), Task
---

# /refactor

## 実行フロー

### Step 1: リファクタリング対象の理解

対象ファイルを Read で読み、現状を把握する。

### Step 2: 既存テストの確認（重要）

`test-runner` で対象に関連するテストを実行:

> Task: test-runner で関連テストを実行。

**赤いテストがある状態でリファクタリングを始めない。** 必ずすべてグリーンの状態から開始する。

### Step 3: 影響範囲の分析

`impact-analyzer` で影響範囲を確認:

> Task: impact-analyzer でリファクタリング対象の影響範囲を分析。

### Step 4: リファクタリング計画

`.steering/[現在のタスク]/design.md` に記入:

- 何をどう変えるか
- なぜ変えるか
- 既存の振る舞いを変えないことの保証方法
- 段階的な変更ステップ（小さな単位に分割）
- 各ステップでテストを実行する計画

ユーザーに承認を求める。

### Step 5: 段階的な変更

> **重要**: 一度に大きな変更をしない。小さなステップに分け、各ステップ後にテストを実行する。

各ステップ:
1. 変更を実施（最小限の単位で）
2. `test-runner` でテスト実行
3. 失敗があれば即座にロールバック
4. tasklist のチェックを更新
5. git commit（小さなコミットで履歴を残す）

### Step 6: 最終レビュー

`code-reviewer` で全体をレビュー:

> Task: code-reviewer で変更全体をレビュー。リファクタリングの観点（可読性、保守性、設計の改善）を重視。

### Step 7: 完了処理

`/finish-task` を実行する。

## 制約

- 振る舞いを変える変更は含めない（リファクタリングの定義違反）
- 既存テストを変更しない（新規追加は OK）
- 大きな変更を一度に行わない
- テストが赤い状態でリファクタリングを始めない
```

ユーザー承認 + Grill me。

#### 3.5 `/review-changes`

```markdown
---
description: >
  直近の git 変更を多角的にレビューする。code-reviewer と security-checker を
  起動し、結果を統合して報告する。コミット前、PR 作成前に実行する。
  Shell Preprocessing で git の現状を動的に取得する。
allowed-tools: Read, Bash(git *), Task
---

# /review-changes

## 現在の状況
!`git status --short`

## 変更統計
!`git diff --stat HEAD`

## 実行フロー

### Step 1: 変更の有無確認

上記の動的データから変更を確認。変更がない場合は中断:

> 「変更がありません。レビュー対象がないため終了します。」

### Step 2: code-reviewer の起動

`code-reviewer` サブエージェントを起動:

> Task: code-reviewer で直近の git diff をレビュー。HIGH/MEDIUM の指摘を優先的に。

### Step 3: security-checker の起動

外部入力を扱う変更や、認証/認可に関わる変更がある場合、`security-checker` を起動:

> Task: security-checker で変更内容のセキュリティリスクを調査。

### Step 4: 結果の統合

両エージェントからのレポートを統合し、以下の形式で表示:

\`\`\`markdown
## 変更レビュー結果

### 変更概要
- 変更ファイル数: N
- 追加行数: +N
- 削除行数: -N

### CRITICAL/HIGH（必須対応）
[統合した指摘]

### MEDIUM（推奨対応）
[統合した指摘]

### LOW（任意対応）
[統合した指摘]

### 良かった点
[code-reviewer が評価した点]
\`\`\`

### Step 5: ユーザーへの提案

- CRITICAL/HIGH があれば: 「これらを修正してから commit してください」
- なければ: 「commit して問題ありません」

## 制約

- 全レポートを生で流さない（統合・要約する）
- 重要な指摘を見落とさない
- 「問題なし」で終わらせる場合も理由を述べる
```

ユーザー承認 + Grill me。

#### 3.6 `/smart-compact`

```markdown
---
description: >
  重要情報を明示的に保持した compact を実行する。
  単なる /compact ではなく、設計判断、未解決事項、決定事項を必ず保持する。
  コンテキスト使用率が 50% を超えた時、長いセッションで品質劣化を感じた時に実行する。
---

# /smart-compact

## 実行フロー

### Step 1: 現在のコンテキスト確認

ユーザーに `/context` の実行を依頼。

50% 未満の場合:

> 「現在のコンテキスト使用率は [N]% です。compact は不要です。50% を超えてから実行することを推奨します。」

50% 以上の場合は次へ。

### Step 2: タスクの継続性確認

ユーザーに尋ねる:

> 「現在のタスクをこのまま続けますか? それとも別のタスクに切り替えますか?」

- **続ける** → Step 3 へ
- **切り替える** → 「`/clear` を使うことを推奨します。compact ではなく完全リセットの方が次のタスクに適しています。」と通知して終了

### Step 3: 重要情報の確認

ユーザーに尋ねる:

> 「現在のセッションで保持すべき特に重要な情報はありますか? 例えば、特定の設計判断、未解決のバグ、ユーザーから受けた制約など。」

回答を待つ。

### Step 4: compact の実行

以下のプロンプトで compact を実行:

\`\`\`
/compact 以下を必ず保持してください:
(1) このセッションで決定したアーキテクチャ判断とその根拠
(2) 未解決の TODO、ブロッカー、待機中の依存関係
(3) ユーザーが明示的に拒否した実装方針とその理由
(4) 採用したライブラリ・パッケージとバージョン
(5) 実行したテストとその結果
(6) [Step 3 でユーザーが指定した追加の重要情報]

詳細なコード断片、会話の枝葉、解決済みの議論は省略可。
\`\`\`

### Step 5: compact 後の確認

ユーザーに `/context` と `/memory` を実行してもらい、以下を確認:

- 使用率が下がったか
- CLAUDE.md がまだロードされているか
- 必要な情報が保持されているか

## 使用タイミング

- コンテキスト使用率が 50% を超えた時
- 大きな機能実装が完了した直後
- 長いデバッグセッション後
- 方針転換するとき（ただし完全な切り替えは `/clear` を推奨）

## アンチパターン

- ❌ コンテキストが 80% を超えてから実行する（手遅れ）
- ❌ タスクが完全に切り替わる時に使う（その時は `/clear`）
- ❌ Step 3 の重要情報の確認を省略する
```

ユーザー承認 + Grill me。

#### 3.7 `/finish-task`

```markdown
---
description: >
  タスクの完了処理を行う。.steering の最終化、最終レビュー、テスト実行、
  コミット提案までを一連の流れで実行する。
  /add-feature, /fix-bug, /refactor の完了後に必ず実行する。
allowed-tools: Read, Write, Edit, Bash(git *), Task
---

# /finish-task

## 実行フロー

### Step 1: tasklist の最終確認

`.steering/[現在のタスク]/tasklist.md` を Read で確認。

未完了のタスクがあれば、ユーザーに確認:

> 「以下のタスクが未完了です:
> - タスク 1
> - タスク 2
>
> これらを完了させますか? それとも次のタスクに繰り越しますか?」

### Step 2: design.md の最終化

実装中に判明した設計の変更や追加情報を反映する。
当初の設計から変わった点があれば明記する。

### Step 3: blockers.md / decisions.md の作成（任意）

実装中にブロッカーが発生した場合は `blockers.md` を作成。
重要な設計判断があった場合は `decisions.md` を作成。

ユーザーに尋ねる:

> 「このタスクで特筆すべきブロッカーや重要な設計判断はありましたか?
> あれば blockers.md / decisions.md に記録します。」

### Step 4: 最終レビュー

`/review-changes` を呼び出す:

> /review-changes を実行してください。

CRITICAL/HIGH の指摘があれば対応する。

### Step 5: テスト実行

`test-runner` を起動:

> Task: test-runner で全テストを実行。

すべて通ることを確認。

### Step 6: コミットメッセージの提案

ユーザーに提案:

\`\`\`
[type]: [短い説明]

- 変更内容 1
- 変更内容 2
- 変更内容 3

Refs: .steering/[YYYYMMDD]-[task-name]/
\`\`\`

type の選択肢:
- `feat`: 新機能
- `fix`: バグ修正
- `refactor`: リファクタリング
- `docs`: ドキュメント
- `test`: テスト
- `chore`: その他

### Step 7: コミット実行

ユーザーが承認したら git commit を実行。

### Step 8: 完了通知

\`\`\`
タスク完了です!

作成・更新したファイル:
- .steering/[YYYYMMDD]-[task-name]/requirement.md
- .steering/[YYYYMMDD]-[task-name]/design.md
- .steering/[YYYYMMDD]-[task-name]/tasklist.md
- (blockers.md, decisions.md があれば)
- (実装したコードファイル)

次のタスクを始める前に `/clear` でセッションをリセットすることを強く推奨します。
\`\`\`

## 制約

- テストが失敗している状態で完了しない
- CRITICAL/HIGH の指摘を残したまま完了しない
- .steering の記録を省略しない
- ユーザー承認なしで commit しない
```

ユーザー承認 + Grill me。

### Step 4: 全コマンドの整合性レビュー

```bash
ls -la .claude/commands/
```

すべてのコマンドが作成されたことを確認。

整合性チェック:

- [ ] 単一責任の原則を満たしているか
- [ ] 各コマンドが Skill と Agent を適切に呼び出しているか
- [ ] コマンド間の連携（/start-task → /add-feature → /finish-task）がスムーズか
- [ ] 重複するコマンドはないか
- [ ] アンチパターンが明示されているか

### Step 5: 進捗ファイルの更新

`.steering/_setup-progress.md` の Phase 5 を完了マーク + 相互参照マップ更新:

```markdown
- [x] **Phase 5: /setup-commands** — ワークフローコマンド群
  - 完了日時: [YYYY-MM-DD HH:MM]
  - 作成コマンド:
    - /start-task
    - /add-feature
    - /fix-bug
    - /refactor
    - /review-changes
    - /smart-compact
    - /finish-task

### Agent → Command 参照
- file-finder → /add-feature, /fix-bug
- impact-analyzer → /add-feature, /fix-bug, /refactor
- code-reviewer → /add-feature, /fix-bug, /refactor, /review-changes, /finish-task
- security-checker → /add-feature, /review-changes
- test-runner → /add-feature, /fix-bug, /refactor, /finish-task
- test-analyzer → /add-feature, /fix-bug
- log-analyzer → /fix-bug
```

### Step 6: 完了通知

```
Phase 5 完了です。

作成したコマンド: 7 個
- ライフサイクル: /start-task, /finish-task
- ワークフロー: /add-feature, /fix-bug, /refactor
- ユーティリティ: /review-changes, /smart-compact

次のステップ:
1. `/clear` でリセット
2. `/model sonnet` を維持
3. `/setup-hooks` を実行
```

## 完了条件

- [ ] 7 つのコマンドすべてが作成されている
- [ ] 各コマンドに明確な実行フローが記述されている
- [ ] 各コマンドが適切に Skill と Agent を呼び出している
- [ ] 各コマンドで Grill me ステップ実施済み
- [ ] 進捗ファイルの相互参照マップが更新されている

## アンチパターン

- ❌ 複数のコマンドを一気に作成する
- ❌ 抽象的なステップを記述する
- ❌ Skill や Agent を呼ばずに全部メインエージェントで処理する
- ❌ 単一責任を破る
- ❌ 実行フローの順序を曖昧にする
- ❌ Grill me を省略する
