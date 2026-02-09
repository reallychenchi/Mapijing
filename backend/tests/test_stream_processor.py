"""流式处理器测试."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.stream_processor import StreamProcessor, TTSChunk
from services.text_splitter import TextSplitter
from services.tts_service import TTSConfig, TTSResult, TTSService
from services.llm_service import LLMConfig, LLMService
from services.emotion_parser import EmotionParser


class TestTTSChunk:
    """TTSChunk 测试类."""

    def test_chunk_creation(self) -> None:
        """创建 TTSChunk."""
        chunk = TTSChunk(
            text="你好",
            audio=b"audio_data",
            seq=1,
            is_final=False,
        )

        assert chunk.text == "你好"
        assert chunk.audio == b"audio_data"
        assert chunk.seq == 1
        assert chunk.is_final is False

    def test_final_chunk(self) -> None:
        """最终片段."""
        chunk = TTSChunk(
            text="",
            audio=b"",
            seq=5,
            is_final=True,
        )

        assert chunk.is_final is True


class TestStreamProcessor:
    """StreamProcessor 测试类."""

    @pytest.fixture
    def mock_llm_service(self) -> MagicMock:
        """Mock LLM 服务."""
        service = MagicMock(spec=LLMService)
        return service

    @pytest.fixture
    def mock_tts_service(self) -> MagicMock:
        """Mock TTS 服务."""
        service = MagicMock(spec=TTSService)
        return service

    @pytest.fixture
    def emotion_parser(self) -> EmotionParser:
        """情感解析器."""
        return EmotionParser()

    def test_clean_text_for_tts(
        self, mock_llm_service: MagicMock, mock_tts_service: MagicMock
    ) -> None:
        """清理文本以便 TTS 合成."""
        processor = StreamProcessor(
            llm_service=mock_llm_service,
            tts_service=mock_tts_service,
        )

        # 测试移除 content 标签
        text = "<content>你好</content>"
        result = processor._clean_text_for_tts(text)
        assert result == "你好"

        # 测试移除 emotion 标签
        text = "你好<emotion>共情倾听</emotion>"
        result = processor._clean_text_for_tts(text)
        assert result == "你好"

        # 测试混合标签
        text = "<content>我理解你</content><emotion>安慰支持</emotion>"
        result = processor._clean_text_for_tts(text)
        assert result == "我理解你"

        # 测试无标签
        text = "普通文本"
        result = processor._clean_text_for_tts(text)
        assert result == "普通文本"

    def test_interrupt(
        self, mock_llm_service: MagicMock, mock_tts_service: MagicMock
    ) -> None:
        """中断处理."""
        processor = StreamProcessor(
            llm_service=mock_llm_service,
            tts_service=mock_tts_service,
        )

        assert processor._interrupted is False
        processor.interrupt()
        assert processor._interrupted is True

    def test_reset(
        self, mock_llm_service: MagicMock, mock_tts_service: MagicMock
    ) -> None:
        """重置状态."""
        processor = StreamProcessor(
            llm_service=mock_llm_service,
            tts_service=mock_tts_service,
        )

        # 设置一些状态
        processor._interrupted = True
        processor.text_splitter.buffer = "some text"

        # 重置
        processor.reset()

        assert processor._interrupted is False
        assert processor.text_splitter.buffer == ""

    @pytest.mark.asyncio
    async def test_process_with_mock(
        self, mock_llm_service: MagicMock, mock_tts_service: MagicMock
    ) -> None:
        """使用 Mock 测试处理流程."""
        # 设置 LLM 流式返回
        async def mock_chat_stream(messages: list) -> AsyncMock:
            for text in ["你好。", "我是小马。"]:
                yield text

        mock_llm_service.chat_stream = mock_chat_stream

        # 设置 TTS 返回
        mock_tts_service.synthesize = AsyncMock(
            return_value=TTSResult(
                audio_data=b"audio",
                duration_ms=100,
                success=True,
            )
        )

        processor = StreamProcessor(
            llm_service=mock_llm_service,
            tts_service=mock_tts_service,
        )

        # 收集结果
        chunks: list[TTSChunk] = []
        async for chunk in processor.process([{"role": "user", "content": "你好"}]):
            chunks.append(chunk)

        # 应该有 2 个文本片段
        assert len(chunks) >= 2
        assert all(isinstance(c, TTSChunk) for c in chunks)

    @pytest.mark.asyncio
    async def test_process_with_emotion_callback(
        self, mock_llm_service: MagicMock, mock_tts_service: MagicMock
    ) -> None:
        """测试情感回调."""
        # 设置 LLM 流式返回包含情感标签
        async def mock_chat_stream(messages: list) -> AsyncMock:
            yield "<content>我理解你。</content><emotion>共情倾听</emotion>"

        mock_llm_service.chat_stream = mock_chat_stream

        # 设置 TTS 返回
        mock_tts_service.synthesize = AsyncMock(
            return_value=TTSResult(
                audio_data=b"audio",
                duration_ms=100,
                success=True,
            )
        )

        processor = StreamProcessor(
            llm_service=mock_llm_service,
            tts_service=mock_tts_service,
        )

        # 情感回调
        emotion_received: list[str] = []

        async def on_emotion(emotion: str) -> None:
            emotion_received.append(emotion)

        # 处理
        chunks: list[TTSChunk] = []
        async for chunk in processor.process(
            [{"role": "user", "content": "我不开心"}],
            on_emotion=on_emotion,
        ):
            chunks.append(chunk)

        # 验证情感被正确解析
        assert "共情倾听" in emotion_received

    @pytest.mark.asyncio
    async def test_process_tts_failure(
        self, mock_llm_service: MagicMock, mock_tts_service: MagicMock
    ) -> None:
        """TTS 失败时仍然发送文字."""
        async def mock_chat_stream(messages: list) -> AsyncMock:
            yield "你好。"

        mock_llm_service.chat_stream = mock_chat_stream

        # TTS 返回失败
        mock_tts_service.synthesize = AsyncMock(
            return_value=TTSResult(
                audio_data=b"",
                duration_ms=0,
                success=False,
                error_message="TTS failed",
            )
        )

        processor = StreamProcessor(
            llm_service=mock_llm_service,
            tts_service=mock_tts_service,
        )

        chunks: list[TTSChunk] = []
        async for chunk in processor.process([{"role": "user", "content": "你好"}]):
            chunks.append(chunk)

        # 应该仍然有文字，但没有音频
        text_chunks = [c for c in chunks if c.text]
        assert len(text_chunks) >= 1
        assert text_chunks[0].audio == b""
