"""会话服务 - 整合 ASR + LLM."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from services.context_manager import ContextConfig, ContextManager
from services.llm_service import LLMConfig, LLMService

logger = logging.getLogger(__name__)


@dataclass
class ConversationConfig:
    """会话配置."""

    llm_config: LLMConfig
    context_config: ContextConfig = field(default_factory=ContextConfig)


class ConversationService:
    """会话服务."""

    DEFAULT_EMOTION: str = "默认陪伴"

    def __init__(self, config: ConversationConfig) -> None:
        """
        初始化会话服务.

        Args:
            config: 会话配置
        """
        self.config = config
        self.llm_service = LLMService(config.llm_config)
        self.context_manager = ContextManager(config=config.context_config)
        self.current_emotion = self.DEFAULT_EMOTION

    async def process_user_input(
        self,
        user_text: str,
        on_emotion_change: Callable[[str], Awaitable[None]] | None = None,
        on_llm_response: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """
        处理用户输入，返回 LLM 回复.

        Args:
            user_text: 用户输入文字（ASR 识别结果）
            on_emotion_change: 情感变化回调
            on_llm_response: LLM 回复回调

        Returns:
            LLM 回复文字
        """
        # 1. 添加用户消息到上下文
        self.context_manager.add_user_message(user_text)
        logger.info(f"User input: {user_text[:50]}...")

        # 2. 调用 LLM
        messages = self.context_manager.get_messages()
        response = await self.llm_service.chat_non_stream(messages)
        logger.info(f"LLM response: {response.content[:50]}...")

        # 3. 处理情感变化
        if response.emotion != self.current_emotion:
            old_emotion = self.current_emotion
            self.current_emotion = response.emotion
            logger.info(f"Emotion changed: {old_emotion} -> {response.emotion}")
            if on_emotion_change:
                await on_emotion_change(response.emotion)

        # 4. 添加助手消息到上下文
        self.context_manager.add_assistant_message(response.content)

        # 5. 回调通知
        if on_llm_response:
            await on_llm_response(response.content)

        return response.content

    def get_current_emotion(self) -> str:
        """获取当前情感状态."""
        return self.current_emotion

    def reset(self) -> None:
        """重置会话."""
        self.context_manager.clear()
        self.current_emotion = self.DEFAULT_EMOTION
        logger.info("Conversation reset")

    async def close(self) -> None:
        """关闭服务."""
        await self.llm_service.close()
        logger.info("Conversation service closed")
