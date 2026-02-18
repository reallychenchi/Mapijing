"""应用配置."""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings."""

    # Application
    APP_NAME: str = "Mapijing API"
    APP_VERSION: str = "1.0.0"

    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL: str = os.getenv(
        "DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"
    )
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_MAX_TOKENS: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "2048"))
    DEEPSEEK_TEMPERATURE: float = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))

    # 上下文管理
    CONTEXT_MAX_TOKENS: int = int(os.getenv("CONTEXT_MAX_TOKENS", "50000"))

    # 火山引擎 ASR 配置
    VOLC_ASR_URL: str = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
    VOLC_ASR_APP_ID: str = os.getenv("VOLC_ASR_APP_ID", "")
    VOLC_ASR_ACCESS_KEY: str = os.getenv("VOLC_ASR_ACCESS_KEY", "")

    # 火山引擎 TTS 配置
    VOLC_TTS_URL: str = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
    VOLC_TTS_APP_ID: str = os.getenv("VOLC_TTS_APP_ID", "")
    VOLC_TTS_ACCESS_KEY: str = os.getenv("VOLC_TTS_ACCESS_KEY", "")
    VOLC_TTS_CLUSTER: str = os.getenv("VOLC_TTS_CLUSTER", "volcano_tts")
    VOLC_TTS_VOICE_TYPE: str = os.getenv(
        "VOLC_TTS_VOICE_TYPE", "zh_female_cancan_mars_bigtts"
    )
    VOLC_TTS_SPEED_RATIO: float = float(os.getenv("VOLC_TTS_SPEED_RATIO", "1.0"))
    VOLC_TTS_VOLUME_RATIO: float = float(os.getenv("VOLC_TTS_VOLUME_RATIO", "1.0"))

    # 火山引擎端到端实时语音大模型配置
    # 复用 ASR 的 APP_ID 和 ACCESS_KEY
    VOLC_E2E_APP_ID: str = os.getenv("VOLC_E2E_APP_ID", "") or os.getenv("VOLC_ASR_APP_ID", "")
    VOLC_E2E_ACCESS_KEY: str = os.getenv("VOLC_E2E_ACCESS_KEY", "") or os.getenv("VOLC_ASR_ACCESS_KEY", "")
    VOLC_E2E_MODEL: str = os.getenv("VOLC_E2E_MODEL", "O")  # O, SC, 1.2.1.0, 2.2.0.0
    VOLC_E2E_SPEAKER: str = os.getenv("VOLC_E2E_SPEAKER", "zh_female_vv_jupiter_bigtts")
    VOLC_E2E_BOT_NAME: str = os.getenv("VOLC_E2E_BOT_NAME", "小马")
    VOLC_E2E_SYSTEM_ROLE: str = os.getenv(
        "VOLC_E2E_SYSTEM_ROLE",
        "你是一个友善、温暖的AI助手，名叫小马。你善于倾听，能够给予用户情感支持和陪伴。"
    )
    VOLC_E2E_SPEAKING_STYLE: str = os.getenv(
        "VOLC_E2E_SPEAKING_STYLE",
        "你的说话风格简洁明了，语速适中，语调自然，充满关怀。"
    )

    # Emotion types
    EMOTION_TYPES: list[str] = ["默认陪伴", "共情倾听", "安慰支持", "轻松愉悦"]


settings = Settings()
