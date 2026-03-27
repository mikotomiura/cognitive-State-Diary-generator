# 設計: レビュー Critical 3件の修正

## C-01: field_validator → model_validator に変更
schemas.py の limit_entries を model_validator(mode="after") に変更し、self.window_size を参照。

## C-02: MemoryManager に config パラメータ追加
- MemoryManager.__init__ に temperature_final: float = 0.3 を追加
- pipeline.py の MemoryManager 生成で config.temperature_final を渡す
- memory.py の温度ハードコードを self._temperature_final に変更

## C-03: Critic のデッドコード削除
- _build_critic_prompt メソッドを削除
- _client, _config, _prompts_dir フィールドを削除
- Critic.__init__ の docstring を追加
