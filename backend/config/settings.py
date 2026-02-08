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

    # 火山引擎 TTS 配置（阶段 5 使用）
    VOLC_TTS_URL: str = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
    VOLC_TTS_APP_ID: str = os.getenv("VOLC_TTS_APP_ID", "")
    VOLC_TTS_ACCESS_KEY: str = os.getenv("VOLC_TTS_ACCESS_KEY", "")
    VOLC_TTS_CLUSTER: str = os.getenv("VOLC_TTS_CLUSTER", "volcano_tts")

    # Emotion types
    EMOTION_TYPES: list[str] = ["默认陪伴", "共情倾听", "安慰支持", "轻松愉悦"]


settings = Settings()
