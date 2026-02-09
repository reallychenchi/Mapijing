"""流式处理器 - 整合 LLM 流式输出 + 分句 + TTS."""

import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass

from services.emotion_parser import EmotionParser
from services.llm_service import LLMService
from services.text_splitter import TextSplitter
from services.tts_service import TTSService

logger = logging.getLogger(__name__)


@dataclass
class TTSChunk:
    """TTS 片段."""

    text: str  # 文字内容
    audio: bytes  # MP3 音频
    seq: int  # 序号
    is_final: bool  # 是否最后一个


class StreamProcessor:
    """流式处理器：LLM + 分句 + TTS."""

    def __init__(
        self,
        llm_service: LLMService,
        tts_service: TTSService,
        emotion_parser: EmotionParser | None = None,
    ) -> None:
        """初始化流式处理器.

        Args:
            llm_service: LLM 服务
            tts_service: TTS 服务
            emotion_parser: 情感解析器（可选）
        """
        self.llm_service = llm_service
        self.tts_service = tts_service
        self.emotion_parser = emotion_parser or EmotionParser()
        self.text_splitter = TextSplitter()
        self._interrupted = False

    async def process(
        self,
        messages: list[dict[str, str]],
        on_emotion: Callable[[str], Awaitable[None]] | None = None,
    ) -> AsyncGenerator[TTSChunk, None]:
        """处理对话，流式返回 tts_chunk.

        Args:
            messages: 对话历史
            on_emotion: 情感变化回调

        Yields:
            TTSChunk 对象
        """
        full_response = ""
        seq = 0
        self._interrupted = False
        self.text_splitter.reset()

        try:
            # 流式获取 LLM 输出
            async for text_chunk in self.llm_service.chat_stream(messages):
                if self._interrupted:
                    logger.info("Stream processing interrupted")
                    break

                full_response += text_chunk

                # 分句
                for sentence in self.text_splitter.feed(text_chunk):
                    if self._interrupted:
                        break

                    seq += 1
                    logger.debug(f"Processing sentence {seq}: {sentence[:30]}...")

                    # 从句子中提取纯文本（去掉可能的标签）
                    clean_sentence = self._clean_text_for_tts(sentence)

                    if clean_sentence:
                        # 合成语音
                        tts_result = await self.tts_service.synthesize(clean_sentence)

                        if tts_result.success:
                            yield TTSChunk(
                                text=clean_sentence,
                                audio=tts_result.audio_data,
                                seq=seq,
                                is_final=False,
                            )
                        else:
                            # TTS 失败时仍然发送文字
                            logger.warning(f"TTS failed for sentence: {tts_result.error_message}")
                            yield TTSChunk(
                                text=clean_sentence,
                                audio=b"",
                                seq=seq,
                                is_final=False,
                            )

            # 处理剩余文本
            if not self._interrupted:
                remaining = self.text_splitter.flush()
                if remaining:
                    clean_remaining = self._clean_text_for_tts(remaining)
                    if clean_remaining:
                        seq += 1
                        tts_result = await self.tts_service.synthesize(clean_remaining)

                        if tts_result.success:
                            yield TTSChunk(
                                text=clean_remaining,
                                audio=tts_result.audio_data,
                                seq=seq,
                                is_final=False,
                            )
                        else:
                            yield TTSChunk(
                                text=clean_remaining,
                                audio=b"",
                                seq=seq,
                                is_final=False,
                            )

            # 解析情感（从完整响应）
            if on_emotion and full_response:
                parsed = self.emotion_parser.parse(full_response)
                if parsed.emotion:
                    await on_emotion(parsed.emotion)

        except Exception as e:
            logger.error(f"Stream processing error: {e}")
            raise

    def _clean_text_for_tts(self, text: str) -> str:
        """清理文本以便 TTS 合成.

        移除 XML 标签，只保留纯文本内容。
        """
        import re

        # 移除 <content></content> 标签
        text = re.sub(r"</?content>", "", text)
        # 移除 <emotion>...</emotion> 标签及内容
        text = re.sub(r"<emotion>.*?</emotion>", "", text, flags=re.DOTALL)
        # 移除其他可能的 XML 标签
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()

    def interrupt(self) -> None:
        """中断处理."""
        self._interrupted = True
        logger.info("Stream processor interrupted")

    def reset(self) -> None:
        """重置状态."""
        self.text_splitter.reset()
        self._interrupted = False
