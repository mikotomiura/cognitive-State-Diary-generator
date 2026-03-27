# 要件定義: レビュー Critical 3件の修正

## C-01: ShortTermMemory.limit_entries が window_size を無視
- **症状:** field_validator は他フィールドにアクセスできず、固定値10でクランプ
- **期待:** window_size に連動してエントリを制限する
- **影響:** schemas.py

## C-02: memory.py の temperature=0.3 がマジックナンバー
- **症状:** MemoryManager が CSDGConfig を受け取らず、温度がハードコード
- **期待:** config.temperature_final 経由で取得
- **影響:** memory.py, pipeline.py (MemoryManager 生成箇所)

## C-03: Critic._build_critic_prompt がデッドコード
- **症状:** CriticPipeline 移行後、呼び出し箇所なし。_client, _config, _prompts_dir も未使用
- **期待:** デッドコードと未使用フィールドを削除
- **影響:** critic.py

## 受け入れ条件
- [ ] ShortTermMemory が window_size でエントリを制限する
- [ ] memory.py の温度が config から取得される
- [ ] Critic のデッドコードが削除されている
- [ ] 全テスト Pass、mypy --strict クリーン
