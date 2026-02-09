"""错误处理工具模块."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(Enum):
    """错误码枚举."""

    ASR_ERROR = "ASR_ERROR"
    LLM_ERROR = "LLM_ERROR"
    TTS_ERROR = "TTS_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class AppError:
    """应用错误数据类."""

    code: ErrorCode
    message: str
    details: str | None = None


def create_error_message(error: AppError) -> dict[str, Any]:
    """创建错误消息."""
    return {
        "type": "error",
        "data": {
            "code": error.code.value,
            "message": error.message,
        },
    }


def create_error_from_exception(
    exception: Exception, error_code: ErrorCode, default_message: str
) -> AppError:
    """从异常创建 AppError."""
    return AppError(
        code=error_code,
        message=default_message,
        details=str(exception),
    )
