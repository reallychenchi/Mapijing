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
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/chat/completions"

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
