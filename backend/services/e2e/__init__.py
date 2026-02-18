"""端到端实时语音对话服务模块."""

from .config import E2EConfig
from .service import E2EDialogService

__all__ = ["E2EDialogService", "E2EConfig"]
