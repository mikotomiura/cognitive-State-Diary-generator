"""
設定管理モジュール。

環境変数または .env ファイルからパイプライン設定を読み込む。
architecture.md §5.2 および functional-design.md §5.4 の仕様に準拠する。
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class VetoCaps(BaseModel):
    """Veto 権発動時のスコア上限キャップ設定。"""

    persona: float = Field(default=2.0, description="ペルソナ軸の veto 上限キャップ")
    temporal: float = Field(default=2.0, description="時間的整合性軸の veto 上限キャップ")
    emotional: float = Field(default=2.0, description="感情的妥当性軸の veto 上限キャップ")
    all_axes: float = Field(default=2.0, description="全軸共通の veto 上限キャップ")


class CriticWeights(BaseModel):
    """Critic 3層分解の重み設定。"""

    rule_based: float = Field(default=0.40, description="Layer 1 (RuleBased) の重み")
    statistical: float = Field(default=0.35, description="Layer 2 (Statistical) の重み")
    llm_judge: float = Field(default=0.25, description="Layer 3 (LLMJudge) の重み")


class StateTransitionConfig(BaseModel):
    """状態遷移の半数式化設定。

    決定論的骨格 + LLM delta 補正 + 微小ノイズの重みを制御する。
    """

    decay_rate: float = Field(default=0.1, description="前日値の減衰率")
    event_weight: float = Field(default=0.6, description="イベントインパクトの重み")
    llm_weight: float = Field(default=0.3, description="LLM delta 補正の重み")
    noise_scale: float = Field(default=0.05, description="微小ノイズの標準偏差")
    clamp_min: float = Field(default=-1.0, description="クランプ下限値")
    clamp_max: float = Field(default=1.0, description="クランプ上限値")
    max_llm_delta: float = Field(default=0.3, description="LLM delta の最大絶対値")


class CSDGConfig(BaseSettings):
    """CSDG パイプライン設定。

    環境変数のプレフィックス ``CSDG_`` から各フィールドを読み込む。
    例: ``CSDG_LLM_API_KEY``, ``CSDG_LLM_MODEL`` など。
    """

    model_config = {"env_prefix": "CSDG_", "env_file": ".env", "env_file_encoding": "utf-8"}

    # LLM設定: プロバイダー選択
    llm_provider: str = "anthropic"  # "anthropic" or "gemini"

    # Anthropic 専用
    anthropic_api_key: str = Field(default="", exclude=True)
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_base_url: str = "https://api.anthropic.com"

    # Gemini 専用
    gemini_api_key: str = Field(default="", exclude=True)
    gemini_model: str = "gemini-2.0-flash"
    gemini_fallback_models: str = ""  # カンマ区切り

    # パイプライン設定
    max_retries: int = 3
    initial_temperature: float = 0.7
    temperature_decay_step: float = 0.2
    memory_window_size: int = 3

    # 感情感度係数
    emotion_sensitivity_stress: float = -0.45
    emotion_sensitivity_motivation: float = 0.4
    emotion_sensitivity_fatigue: float = -0.2

    # Critic 重み設定
    critic_weight_rule_based: float = 0.40
    critic_weight_statistical: float = 0.35
    critic_weight_llm_judge: float = 0.25

    # 状態遷移設定
    state_transition_decay_rate: float = 0.15
    state_transition_event_weight: float = 0.75
    state_transition_llm_weight: float = 0.3
    state_transition_noise_scale: float = 0.05
    state_transition_max_llm_delta: float = 0.3

    # Veto キャップ設定
    veto_cap_persona: float = 2.0
    veto_cap_temporal: float = 2.0
    veto_cap_emotional: float = 2.0
    veto_cap_all_axes: float = 2.0

    # Temperature 設定
    temperature_final: float = 0.3
    temperature_decay_constant: float | None = None

    # 出力
    output_dir: str = "output"

    @property
    def llm_api_key(self) -> str:
        """現在のプロバイダーに応じた API キーを返す。"""
        if self.llm_provider == "gemini":
            return self.gemini_api_key
        return self.anthropic_api_key

    @property
    def llm_model(self) -> str:
        """現在のプロバイダーに応じたモデル名を返す。"""
        if self.llm_provider == "gemini":
            return self.gemini_model
        return self.anthropic_model

    @property
    def emotion_sensitivity(self) -> dict[str, float]:
        """感情感度係数を辞書形式で返す。"""
        return {
            "stress": self.emotion_sensitivity_stress,
            "motivation": self.emotion_sensitivity_motivation,
            "fatigue": self.emotion_sensitivity_fatigue,
        }

    @property
    def critic_weights(self) -> CriticWeights:
        """Critic 重み設定を CriticWeights として返す。"""
        return CriticWeights(
            rule_based=self.critic_weight_rule_based,
            statistical=self.critic_weight_statistical,
            llm_judge=self.critic_weight_llm_judge,
        )

    @property
    def veto_caps(self) -> VetoCaps:
        """Veto キャップ設定を VetoCaps として返す。"""
        return VetoCaps(
            persona=self.veto_cap_persona,
            temporal=self.veto_cap_temporal,
            emotional=self.veto_cap_emotional,
            all_axes=self.veto_cap_all_axes,
        )

    @property
    def state_transition(self) -> StateTransitionConfig:
        """状態遷移設定を StateTransitionConfig として返す。"""
        return StateTransitionConfig(
            decay_rate=self.state_transition_decay_rate,
            event_weight=self.state_transition_event_weight,
            llm_weight=self.state_transition_llm_weight,
            noise_scale=self.state_transition_noise_scale,
            max_llm_delta=self.state_transition_max_llm_delta,
        )

    @property
    def temperature_schedule(self) -> list[float]:
        """リトライ時の Temperature スケジュールを区分線形で返す。

        区分線形の利点:
        - 2回目リトライでも十分な多様性 (0.60) を維持
        - 高インパクト日の「感情崩壊」文体に必要な表現幅を確保
        - 終盤は確実に収束 (0.30) し、物語の着地が安定する

        Returns:
            Temperature のリスト: [0.70, 0.60, 0.45, 0.30]
        """
        return [0.70, 0.60, 0.45, 0.30]
