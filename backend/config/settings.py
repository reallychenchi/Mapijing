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

    # 火山引擎
    VOLCENGINE_ACCESS_KEY: str = os.getenv("VOLCENGINE_ACCESS_KEY", "")
    VOLCENGINE_SECRET_KEY: str = os.getenv("VOLCENGINE_SECRET_KEY", "")
    VOLCENGINE_APP_ID: str = os.getenv("VOLCENGINE_APP_ID", "")

    # Emotion types
    EMOTION_TYPES: list[str] = ["默认陪伴", "共情倾听", "安慰支持", "轻松愉悦"]


settings = Settings()
