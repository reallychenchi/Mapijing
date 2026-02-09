"""会话服务 - 整合 ASR + LLM + TTS."""

import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field

from services.context_manager import ContextConfig, ContextManager
from services.emotion_parser import EmotionParser
from services.llm_service import LLMConfig, LLMService
from services.stream_processor import StreamProcessor, TTSChunk
from services.tts_service import TTSConfig, TTSService

logger = logging.getLogger(__name__)


@dataclass
class ConversationConfig:
    """会话配置."""

    llm_config: LLMConfig
    context_config: ContextConfig = field(default_factory=ContextConfig)
    tts_config: TTSConfig | None = None


class ConversationService:
    """会话服务."""

    DEFAULT_EMOTION: str = "默认陪伴"

    def __init__(self, config: ConversationConfig) -> None:
        """初始化会话服务.

        Args:
            config: 会话配置
        """
        self.config = config
        self.llm_service = LLMService(config.llm_config)
        self.tts_service = TTSService(config.tts_config)
        self.emotion_parser = EmotionParser()
        self.context_manager = ContextManager(config=config.context_config)
        self.stream_processor = StreamProcessor(
            llm_service=self.llm_service,
            tts_service=self.tts_service,
            emotion_parser=self.emotion_parser,
        )
        self.current_emotion = self.DEFAULT_EMOTION

    async def process_user_input(
        self,
        user_text: str,
        on_emotion_change: Callable[[str], Awaitable[None]] | None = None,
        on_llm_response: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """处理用户输入，返回 LLM 回复（非流式，阶段4兼容）.

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

    async def process_user_input_stream(
        self,
        user_text: str,
        on_emotion_change: Callable[[str], Awaitable[None]] | None = None,
    ) -> AsyncGenerator[TTSChunk, None]:
        """处理用户输入，流式返回 TTS 片段（阶段5新增）.

        Args:
            user_text: 用户输入文字（ASR 识别结果）
            on_emotion_change: 情感变化回调

        Yields:
            TTSChunk 对象
        """
        # 1. 添加用户消息到上下文
        self.context_manager.add_user_message(user_text)
        logger.info(f"User input (stream): {user_text[:50]}...")

        # 2. 流式处理
        messages = self.context_manager.get_messages()
        full_text = ""

        async def handle_emotion(emotion: str) -> None:
            """处理情感变化."""
            if emotion != self.current_emotion:
                old_emotion = self.current_emotion
                self.current_emotion = emotion
                logger.info(f"Emotion changed: {old_emotion} -> {emotion}")
                if on_emotion_change:
                    await on_emotion_change(emotion)

        try:
            async for chunk in self.stream_processor.process(
                messages, on_emotion=handle_emotion
            ):
                full_text += chunk.text
                yield chunk

        finally:
            # 3. 添加助手消息到上下文
            if full_text:
                self.context_manager.add_assistant_message(full_text)
                logger.info(f"Stream completed, full text: {full_text[:50]}...")

    def interrupt(self) -> None:
        """中断当前处理."""
        self.stream_processor.interrupt()
        logger.info("Conversation interrupted")

    def get_current_emotion(self) -> str:
        """获取当前情感状态."""
        return self.current_emotion

    def reset(self) -> None:
        """重置会话."""
        self.context_manager.clear()
        self.stream_processor.reset()
        self.current_emotion = self.DEFAULT_EMOTION
        logger.info("Conversation reset")

    async def close(self) -> None:
        """关闭服务."""
        await self.llm_service.close()
        logger.info("Conversation service closed")
