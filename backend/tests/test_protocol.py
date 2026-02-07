"""Protocol 模块单元测试."""

import gzip
import json
import struct

from utils.protocol import (
    HEADER_SIZE,
    PROTOCOL_VERSION,
    CompressionType,
    MsgType,
    MsgTypeFlag,
    SerializationType,
    build_audio_only_request,
    build_full_client_request,
    build_header,
    extract_asr_result,
    parse_error_response,
    parse_response,
)


class TestBuildHeader:
    """build_header 函数测试."""

    def test_basic_header(self) -> None:
        """测试基本头部构建."""
        header = build_header(MsgType.FULL_CLIENT_REQUEST)
        assert len(header) == 4

        # 验证协议版本和头部大小
        byte0 = header[0]
        assert (byte0 >> 4) == PROTOCOL_VERSION
        assert (byte0 & 0x0F) == HEADER_SIZE

    def test_message_type_and_flags(self) -> None:
        """测试消息类型和标志."""
        header = build_header(MsgType.AUDIO_ONLY_REQUEST, flags=MsgTypeFlag.POSITIVE_SEQ)
        byte1 = header[1]
        assert (byte1 >> 4) == MsgType.AUDIO_ONLY_REQUEST
        assert (byte1 & 0x0F) == MsgTypeFlag.POSITIVE_SEQ

    def test_serialization_and_compression(self) -> None:
        """测试序列化和压缩类型."""
        header = build_header(
            MsgType.FULL_CLIENT_REQUEST,
            serialization=SerializationType.JSON,
            compression=CompressionType.GZIP,
        )
        byte2 = header[2]
        assert (byte2 >> 4) == SerializationType.JSON
        assert (byte2 & 0x0F) == CompressionType.GZIP


class TestBuildFullClientRequest:
    """build_full_client_request 函数测试."""

    def test_with_compression(self) -> None:
        """测试带压缩的请求构建."""
        payload = {"key": "value"}
        frame = build_full_client_request(payload, use_compression=True)

        # 解析头部
        header = frame[0:4]
        msg_type = (header[1] >> 4) & 0x0F
        compression = header[2] & 0x0F

        assert msg_type == MsgType.FULL_CLIENT_REQUEST
        assert compression == CompressionType.GZIP

        # 解析 payload size
        payload_size = struct.unpack(">I", frame[4:8])[0]
        assert payload_size > 0

        # 解压并验证
        payload_bytes = frame[8 : 8 + payload_size]
        decompressed = gzip.decompress(payload_bytes)
        decoded = json.loads(decompressed.decode("utf-8"))
        assert decoded == payload

    def test_without_compression(self) -> None:
        """测试不带压缩的请求构建."""
        payload = {"key": "value"}
        frame = build_full_client_request(payload, use_compression=False)

        header = frame[0:4]
        compression = header[2] & 0x0F
        assert compression == CompressionType.NO_COMPRESSION

        payload_size = struct.unpack(">I", frame[4:8])[0]
        payload_bytes = frame[8 : 8 + payload_size]
        decoded = json.loads(payload_bytes.decode("utf-8"))
        assert decoded == payload


class TestBuildAudioOnlyRequest:
    """build_audio_only_request 函数测试."""

    def test_normal_frame(self) -> None:
        """测试普通音频帧."""
        audio_data = b"\x00\x01\x02\x03"
        frame = build_audio_only_request(audio_data, seq=1, is_last=False)

        # 解析头部
        header = frame[0:4]
        msg_type = (header[1] >> 4) & 0x0F
        flags = header[1] & 0x0F

        assert msg_type == MsgType.AUDIO_ONLY_REQUEST
        assert flags == MsgTypeFlag.POSITIVE_SEQ

        # 解析序列号
        seq_value = struct.unpack(">i", frame[4:8])[0]
        assert seq_value == 1

    def test_last_frame(self) -> None:
        """测试最后一帧."""
        audio_data = b"\x00\x01\x02\x03"
        frame = build_audio_only_request(audio_data, seq=5, is_last=True)

        header = frame[0:4]
        flags = header[1] & 0x0F
        assert flags == MsgTypeFlag.NEGATIVE_SEQ_LAST

        # 序列号应该是负数
        seq_value = struct.unpack(">i", frame[4:8])[0]
        assert seq_value == -5

    def test_compression(self) -> None:
        """测试音频压缩."""
        audio_data = b"\x00" * 100
        frame = build_audio_only_request(audio_data, seq=1, is_last=False, use_compression=True)

        header = frame[0:4]
        compression = header[2] & 0x0F
        assert compression == CompressionType.GZIP

    def test_empty_audio(self) -> None:
        """测试空音频数据."""
        frame = build_audio_only_request(b"", seq=1, is_last=True)

        # 空数据不应压缩
        header = frame[0:4]
        compression = header[2] & 0x0F
        assert compression == CompressionType.NO_COMPRESSION


class TestParseResponse:
    """parse_response 函数测试."""

    def test_valid_response(self) -> None:
        """测试有效响应解析."""
        # 构建模拟响应
        payload = {"code": 0, "result": {"text": "测试文本", "utterance_end": False}}
        payload_bytes = json.dumps(payload).encode("utf-8")
        compressed = gzip.compress(payload_bytes)

        header = build_header(
            MsgType.FULL_SERVER_RESPONSE,
            serialization=SerializationType.JSON,
            compression=CompressionType.GZIP,
        )
        payload_size = struct.pack(">I", len(compressed))
        frame = header + payload_size + compressed

        result = parse_response(frame)
        assert result is not None
        assert result["text"] == "测试文本"
        assert result["is_final"] is False

    def test_final_result(self) -> None:
        """测试最终结果."""
        payload = {"code": 0, "result": {"text": "最终文本", "utterance_end": True}}
        payload_bytes = json.dumps(payload).encode("utf-8")

        header = build_header(
            MsgType.FULL_SERVER_RESPONSE,
            serialization=SerializationType.JSON,
            compression=CompressionType.NO_COMPRESSION,
        )
        payload_size = struct.pack(">I", len(payload_bytes))
        frame = header + payload_size + payload_bytes

        result = parse_response(frame)
        assert result is not None
        assert result["is_final"] is True

    def test_too_short_data(self) -> None:
        """测试数据过短."""
        result = parse_response(b"\x00\x01\x02")
        assert result is None

    def test_wrong_message_type(self) -> None:
        """测试错误的消息类型."""
        header = build_header(MsgType.SERVER_ACK)
        frame = header + b"\x00\x00\x00\x00"
        result = parse_response(frame)
        assert result is None


class TestParseErrorResponse:
    """parse_error_response 函数测试."""

    def test_error_response(self) -> None:
        """测试错误响应解析."""
        # 构建错误响应
        header = build_header(MsgType.ERROR, flags=MsgTypeFlag.NO_SEQ)
        error_code = struct.pack(">i", 1001)
        error_msg = json.dumps({"message": "测试错误"}).encode("utf-8")
        payload_size = struct.pack(">I", len(error_msg))

        frame = header + error_code + payload_size + error_msg

        result = parse_error_response(frame)
        assert result is not None
        assert result["error"] is True
        assert result["code"] == 1001
        assert "测试错误" in result["message"]

    def test_too_short_error(self) -> None:
        """测试错误数据过短."""
        result = parse_error_response(b"\x00" * 8)
        assert result is None


class TestExtractAsrResult:
    """extract_asr_result 函数测试."""

    def test_success_result(self) -> None:
        """测试成功结果提取."""
        response = {"code": 0, "result": {"text": "识别文本", "utterance_end": False}}
        result = extract_asr_result(response)
        assert result is not None
        assert result["text"] == "识别文本"
        assert result["is_final"] is False

    def test_error_response(self) -> None:
        """测试错误响应."""
        response = {"code": 1001, "message": "服务错误"}
        result = extract_asr_result(response)
        assert result is not None
        assert result["error"] is True
        assert result["code"] == 1001

    def test_list_format(self) -> None:
        """测试列表格式结果."""
        response = {"code": 0, "result": [{"text": "列表文本", "type": "final"}]}
        result = extract_asr_result(response)
        assert result is not None
        assert result["text"] == "列表文本"
        assert result["is_final"] is True

    def test_empty_result(self) -> None:
        """测试空结果."""
        response = {"code": 0, "result": []}
        result = extract_asr_result(response)
        assert result is None
