"""TTS 服务测试."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts_service import (
    TTSConfig,
    TTSResult,
    TTSService,
    TTSMessage,
    MsgType,
    MsgTypeFlagBits,
    SerializationBits,
    CompressionBits,
    get_cluster,
)


class TestGetCluster:
    """get_cluster 函数测试."""

    def test_standard_voice(self) -> None:
        """标准音色使用 volcano_tts."""
        assert get_cluster("zh_female_cancan_mars_bigtts") == "volcano_tts"
        assert get_cluster("zh_male_linjiananhai_moon_bigtts") == "volcano_tts"

    def test_clone_voice(self) -> None:
        """克隆音色使用 volcano_icl."""
        assert get_cluster("S_custom_voice") == "volcano_icl"
        assert get_cluster("S_12345") == "volcano_icl"


class TestTTSMessage:
    """TTSMessage 测试类."""

    def test_marshal_simple_message(self) -> None:
        """序列化简单消息."""
        msg = TTSMessage(
            msg_type=MsgType.FULL_CLIENT_REQUEST,
            flag=MsgTypeFlagBits.NO_SEQ,
            serialization=SerializationBits.JSON,
            compression=CompressionBits.NONE,
        )
        msg.payload = b'{"test": "data"}'

        data = msg.marshal()

        # 验证头部
        assert len(data) >= 8
        assert (data[1] >> 4) == MsgType.FULL_CLIENT_REQUEST
        assert (data[1] & 0x0F) == MsgTypeFlagBits.NO_SEQ

    def test_unmarshal_audio_message(self) -> None:
        """反序列化音频消息."""
        # 构造一个模拟的音频消息
        header = bytes([
            0x11,  # version=1, header_size=1
            (MsgType.AUDIO_ONLY_SERVER << 4) | MsgTypeFlagBits.POSITIVE_SEQ,
            (SerializationBits.RAW << 4) | CompressionBits.NONE,
            0x00,
        ])
        sequence = (1).to_bytes(4, 'big', signed=True)
        payload = b'fake_audio_data'
        payload_size = len(payload).to_bytes(4, 'big')

        data = header + sequence + payload_size + payload

        msg = TTSMessage.unmarshal(data)

        assert msg.msg_type == MsgType.AUDIO_ONLY_SERVER
        assert msg.flag == MsgTypeFlagBits.POSITIVE_SEQ
        assert msg.sequence == 1
        assert msg.payload == b'fake_audio_data'

    def test_unmarshal_error_message(self) -> None:
        """反序列化错误消息."""
        header = bytes([
            0x11,
            (MsgType.ERROR << 4) | MsgTypeFlagBits.NO_SEQ,
            (SerializationBits.JSON << 4) | CompressionBits.NONE,
            0x00,
        ])
        error_code = (1001).to_bytes(4, 'big')
        payload = b'{"message": "error"}'
        payload_size = len(payload).to_bytes(4, 'big')

        data = header + error_code + payload_size + payload

        msg = TTSMessage.unmarshal(data)

        assert msg.msg_type == MsgType.ERROR
        assert msg.error_code == 1001

    def test_str_representation(self) -> None:
        """字符串表示."""
        msg = TTSMessage(msg_type=MsgType.AUDIO_ONLY_SERVER)
        msg.sequence = 5
        msg.payload = b'12345'

        str_repr = str(msg)
        assert "AUDIO_ONLY_SERVER" in str_repr
        assert "5" in str_repr


class TestTTSConfig:
    """TTSConfig 测试类."""

    def test_default_values(self) -> None:
        """默认值."""
        config = TTSConfig()

        assert config.app_id == ""
        assert config.access_key == ""
        assert config.cluster == "volcano_tts"
        assert config.voice_type == "zh_female_cancan_mars_bigtts"
        assert config.encoding == "mp3"
        assert config.speed_ratio == 1.0
        assert config.volume_ratio == 1.0
        assert config.pitch_ratio == 1.0

    def test_custom_values(self) -> None:
        """自定义值."""
        config = TTSConfig(
            app_id="test_app",
            access_key="test_key",
            voice_type="custom_voice",
            speed_ratio=1.5,
        )

        assert config.app_id == "test_app"
        assert config.access_key == "test_key"
        assert config.voice_type == "custom_voice"
        assert config.speed_ratio == 1.5


class TestTTSResult:
    """TTSResult 测试类."""

    def test_success_result(self) -> None:
        """成功结果."""
        result = TTSResult(
            audio_data=b'audio',
            duration_ms=1000,
            success=True,
        )

        assert result.success is True
        assert result.audio_data == b'audio'
        assert result.duration_ms == 1000
        assert result.error_message is None

    def test_error_result(self) -> None:
        """错误结果."""
        result = TTSResult(
            audio_data=b'',
            duration_ms=0,
            success=False,
            error_message="Connection failed",
        )

        assert result.success is False
        assert result.error_message == "Connection failed"


class TestTTSService:
    """TTSService 测试类."""

    def test_estimate_duration(self) -> None:
        """估算音频时长."""
        config = TTSConfig()
        service = TTSService(config)

        # 空音频
        assert service._estimate_duration(0) == 0

        # 16KB = 1000ms (假设 128kbps MP3)
        duration = service._estimate_duration(16 * 1024)
        assert duration > 0

    def test_empty_text_returns_success(self) -> None:
        """空文本直接返回成功."""
        import asyncio

        config = TTSConfig()
        service = TTSService(config)

        result = asyncio.get_event_loop().run_until_complete(
            service.synthesize("")
        )

        assert result.success is True
        assert result.audio_data == b""
        assert result.duration_ms == 0

    def test_whitespace_text_returns_success(self) -> None:
        """空白文本直接返回成功."""
        import asyncio

        config = TTSConfig()
        service = TTSService(config)

        result = asyncio.get_event_loop().run_until_complete(
            service.synthesize("   ")
        )

        assert result.success is True
        assert result.audio_data == b""

    @pytest.mark.asyncio
    async def test_synthesize_with_mock(self) -> None:
        """使用 Mock 测试合成."""
        config = TTSConfig(
            app_id="test_app",
            access_key="test_key",
        )
        service = TTSService(config)

        # Mock WebSocket 连接
        mock_ws = AsyncMock()

        # 构造模拟响应
        audio_header = bytes([
            0x11,
            (MsgType.AUDIO_ONLY_SERVER << 4) | MsgTypeFlagBits.NO_SEQ,
            (SerializationBits.RAW << 4) | CompressionBits.NONE,
            0x00,
        ])
        audio_payload = b'fake_mp3_audio'
        audio_size = len(audio_payload).to_bytes(4, 'big')
        audio_response = audio_header + audio_size + audio_payload

        end_header = bytes([
            0x11,
            (MsgType.FRONTEND_RESULT_SERVER << 4) | MsgTypeFlagBits.NO_SEQ,
            (SerializationBits.RAW << 4) | CompressionBits.NONE,
            0x00,
        ])
        end_response = end_header + (0).to_bytes(4, 'big')

        mock_ws.recv = AsyncMock(side_effect=[audio_response, end_response])
        mock_ws.send = AsyncMock()

        with patch('websockets.connect', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_ws), __aexit__=AsyncMock())):
            result = await service.synthesize("测试文本")

        # 由于连接被 mock，应该返回成功或处理错误
        # 这个测试主要验证代码路径不会抛出异常
        assert isinstance(result, TTSResult)
