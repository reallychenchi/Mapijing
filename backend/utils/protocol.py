"""火山引擎二进制协议封装."""

import gzip
import json
import struct
from typing import Any

# 协议常量
PROTOCOL_VERSION = 0b0001
HEADER_SIZE = 0b0001


class MsgType:
    """消息类型."""

    FULL_CLIENT_REQUEST = 0b0001
    AUDIO_ONLY_REQUEST = 0b0010
    FULL_SERVER_RESPONSE = 0b1001
    SERVER_ACK = 0b1011
    ERROR = 0b1111


class MsgTypeFlag:
    """消息类型标志."""

    NO_SEQ = 0b0000
    POSITIVE_SEQ = 0b0001
    NEGATIVE_SEQ = 0b0010
    NEGATIVE_SEQ_LAST = 0b0011


class SerializationType:
    """序列化类型."""

    RAW = 0b0000
    JSON = 0b0001


class CompressionType:
    """压缩类型."""

    NO_COMPRESSION = 0b0000
    GZIP = 0b0001


def build_header(
    message_type: int,
    flags: int = 0,
    serialization: int = SerializationType.JSON,
    compression: int = CompressionType.NO_COMPRESSION,
) -> bytes:
    """构建 4 字节协议头."""
    byte0 = (PROTOCOL_VERSION << 4) | HEADER_SIZE
    byte1 = (message_type << 4) | flags
    byte2 = (serialization << 4) | compression
    byte3 = 0x00
    return bytes([byte0, byte1, byte2, byte3])


def build_full_client_request(payload: dict[str, Any], use_compression: bool = True) -> bytes:
    """构建完整客户端请求（初始配置）.

    帧格式 (NoSeq 标志):
    - Header (4 bytes)
    - Payload Size (4 bytes, big endian)
    - Payload (JSON bytes, 可压缩)
    """
    payload_bytes = json.dumps(payload).encode("utf-8")

    if use_compression:
        payload_bytes = gzip.compress(payload_bytes)
        compression = CompressionType.GZIP
    else:
        compression = CompressionType.NO_COMPRESSION

    header = build_header(
        MsgType.FULL_CLIENT_REQUEST,
        flags=MsgTypeFlag.NO_SEQ,
        serialization=SerializationType.JSON,
        compression=compression,
    )

    payload_size = struct.pack(">I", len(payload_bytes))
    return header + payload_size + payload_bytes


def build_audio_only_request(
    audio_data: bytes, seq: int, is_last: bool = False, use_compression: bool = True
) -> bytes:
    """构建仅音频请求.

    帧格式:
    - Header (4 bytes)
    - Sequence (4 bytes, signed int, big endian) - 最后一帧为负数
    - Payload Size (4 bytes, big endian)
    - Payload (audio data, 可压缩)
    """
    if use_compression and len(audio_data) > 0:
        audio_data = gzip.compress(audio_data)
        compression = CompressionType.GZIP
    else:
        compression = CompressionType.NO_COMPRESSION

    flags = MsgTypeFlag.NEGATIVE_SEQ_LAST if is_last else MsgTypeFlag.POSITIVE_SEQ

    header = build_header(
        MsgType.AUDIO_ONLY_REQUEST,
        flags=flags,
        serialization=SerializationType.RAW,
        compression=compression,
    )

    seq_value = -seq if is_last else seq
    seq_bytes = struct.pack(">i", seq_value)
    payload_size = struct.pack(">I", len(audio_data))

    return header + seq_bytes + payload_size + audio_data


def parse_response(data: bytes) -> dict[str, Any] | None:
    """解析服务端响应."""
    if len(data) < 8:
        return None

    # 解析头部
    header = data[0:4]
    msg_type = (header[1] >> 4) & 0x0F
    compression = header[2] & 0x0F

    if msg_type == MsgType.ERROR:
        # 解析错误响应
        return parse_error_response(data)

    if msg_type != MsgType.FULL_SERVER_RESPONSE:
        return None

    # 读取 payload size
    payload_size = struct.unpack(">I", data[4:8])[0]

    if len(data) < 8 + payload_size:
        return None

    payload_bytes = data[8 : 8 + payload_size]

    # 解压缩
    if compression == CompressionType.GZIP:
        try:
            payload_bytes = gzip.decompress(payload_bytes)
        except Exception:
            return None

    # 解析 JSON
    try:
        result = json.loads(payload_bytes.decode("utf-8"))
        return extract_asr_result(result)
    except Exception:
        return None


def parse_error_response(data: bytes) -> dict[str, Any] | None:
    """解析错误响应."""
    if len(data) < 12:
        return None

    header = data[0:4]
    flags = header[1] & 0x0F
    compression = header[2] & 0x0F

    cursor = 4
    # 如果有序列号
    if flags & 0x01:
        cursor += 4

    # 错误码
    error_code = struct.unpack(">i", data[cursor : cursor + 4])[0]
    cursor += 4

    # payload size
    if len(data) < cursor + 4:
        return {"error": True, "code": error_code, "message": "Unknown error"}

    payload_size = struct.unpack(">I", data[cursor : cursor + 4])[0]
    cursor += 4

    if payload_size > 0 and len(data) >= cursor + payload_size:
        error_bytes = data[cursor : cursor + payload_size]

        if compression == CompressionType.GZIP:
            try:
                error_bytes = gzip.decompress(error_bytes)
            except Exception:
                pass

        try:
            error_json = json.loads(error_bytes.decode("utf-8"))
            error_msg = error_json.get("message", str(error_json))
        except Exception:
            error_msg = error_bytes.decode("utf-8", errors="ignore")

        return {"error": True, "code": error_code, "message": error_msg}

    return {"error": True, "code": error_code, "message": "Unknown error"}


def extract_asr_result(response: dict[str, Any]) -> dict[str, Any] | None:
    """从火山引擎响应中提取 ASR 结果."""
    # 检查错误
    if response.get("code", 0) != 0:
        return {
            "error": True,
            "code": response.get("code"),
            "message": response.get("message", "Unknown error"),
        }

    # 提取结果
    result = response.get("result", {})

    # V3 API 格式
    if isinstance(result, dict):
        text = result.get("text", "")
        is_final = result.get("utterance_end", False)
        return {"text": text, "is_final": is_final}

    # 备用格式
    result_list = response.get("result", [])
    if isinstance(result_list, list) and len(result_list) > 0:
        item = result_list[0]
        text = item.get("text", "")
        is_final = item.get("type", "") == "final"
        return {"text": text, "is_final": is_final}

    return None
