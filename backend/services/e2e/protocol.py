"""豆包端到端实时语音大模型 WebSocket 二进制协议处理.

该模块负责构建和解析火山引擎端到端语音API的二进制协议帧。
协议由4字节header、optional字段、payload size和payload组成。
"""

import gzip
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Protocol constants
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message Type
CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

# Message Type Specific Flags
NO_SEQUENCE = 0b0000
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_SEQUENCE_1 = 0b0011
MSG_WITH_EVENT = 0b0100

# Message Serialization
NO_SERIALIZATION = 0b0000
JSON_SERIALIZATION = 0b0001
THRIFT = 0b0011
CUSTOM_TYPE = 0b1111

# Message Compression
NO_COMPRESSION = 0b0000
GZIP_COMPRESSION = 0b0001
CUSTOM_COMPRESSION = 0b1111

# Client Event IDs
EVENT_START_CONNECTION = 1
EVENT_FINISH_CONNECTION = 2
EVENT_START_SESSION = 100
EVENT_FINISH_SESSION = 102
EVENT_TASK_REQUEST = 200
EVENT_SAY_HELLO = 300
EVENT_CHAT_TTS_TEXT = 500
EVENT_CHAT_TEXT_QUERY = 501
EVENT_CHAT_RAG_TEXT = 502

# Server Event IDs
EVENT_CONNECTION_STARTED = 50
EVENT_CONNECTION_FAILED = 51
EVENT_CONNECTION_FINISHED = 52
EVENT_SESSION_STARTED = 150
EVENT_SESSION_FINISHED = 152
EVENT_SESSION_FAILED = 153
EVENT_USAGE_RESPONSE = 154
EVENT_TTS_SENTENCE_START = 350
EVENT_TTS_SENTENCE_END = 351
EVENT_TTS_RESPONSE = 352
EVENT_TTS_ENDED = 359
EVENT_ASR_INFO = 450
EVENT_ASR_RESPONSE = 451
EVENT_ASR_ENDED = 459
EVENT_CHAT_RESPONSE = 550
EVENT_CHAT_TEXT_QUERY_CONFIRMED = 553
EVENT_CHAT_ENDED = 559
EVENT_DIALOG_COMMON_ERROR = 599


def generate_header(
    version: int = PROTOCOL_VERSION,
    message_type: int = CLIENT_FULL_REQUEST,
    message_type_specific_flags: int = MSG_WITH_EVENT,
    serial_method: int = JSON_SERIALIZATION,
    compression_type: int = GZIP_COMPRESSION,
    reserved_data: int = 0x00,
) -> bytearray:
    """生成协议头部.

    Args:
        version: 协议版本，固定为 0b0001
        message_type: 消息类型
        message_type_specific_flags: 消息类型特定标志
        serial_method: 序列化方法
        compression_type: 压缩方法
        reserved_data: 保留字段

    Returns:
        4字节的协议头部
    """
    header = bytearray()
    header_size = DEFAULT_HEADER_SIZE
    header.append((version << 4) | header_size)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serial_method << 4) | compression_type)
    header.append(reserved_data)
    return header


def build_event_frame(
    event_id: int,
    session_id: str,
    payload: dict[str, Any] | None = None,
    message_type: int = CLIENT_FULL_REQUEST,
    serial_method: int = JSON_SERIALIZATION,
) -> bytearray:
    """构建带事件ID的消息帧.

    Args:
        event_id: 事件ID
        session_id: 会话ID
        payload: 消息负载（JSON格式）
        message_type: 消息类型
        serial_method: 序列化方法

    Returns:
        完整的二进制消息帧
    """
    frame = bytearray(generate_header(
        message_type=message_type,
        serial_method=serial_method,
    ))

    # Event ID (4 bytes, big endian)
    frame.extend(event_id.to_bytes(4, 'big'))

    # Session ID (对于Connection级别事件不需要，Session级别事件需要)
    if event_id >= 100:  # Session级别事件
        frame.extend(len(session_id).to_bytes(4, 'big'))
        frame.extend(session_id.encode('utf-8'))

    # Payload
    if payload is None:
        payload = {}
    payload_bytes = json.dumps(payload).encode('utf-8')
    payload_bytes = gzip.compress(payload_bytes)
    frame.extend(len(payload_bytes).to_bytes(4, 'big'))
    frame.extend(payload_bytes)

    return frame


def build_audio_frame(
    event_id: int,
    session_id: str,
    audio_data: bytes,
) -> bytearray:
    """构建音频数据帧.

    Args:
        event_id: 事件ID (通常是 EVENT_TASK_REQUEST = 200)
        session_id: 会话ID
        audio_data: PCM音频数据

    Returns:
        完整的二进制音频帧
    """
    frame = bytearray(generate_header(
        message_type=CLIENT_AUDIO_ONLY_REQUEST,
        serial_method=NO_SERIALIZATION,
    ))

    # Event ID (4 bytes)
    frame.extend(event_id.to_bytes(4, 'big'))

    # Session ID
    frame.extend(len(session_id).to_bytes(4, 'big'))
    frame.extend(session_id.encode('utf-8'))

    # Audio payload (compressed)
    payload_bytes = gzip.compress(audio_data)
    frame.extend(len(payload_bytes).to_bytes(4, 'big'))
    frame.extend(payload_bytes)

    return frame


def parse_response(res: bytes) -> dict[str, Any]:
    """解析服务器响应帧.

    Args:
        res: 服务器返回的二进制数据

    Returns:
        解析后的响应字典，包含 message_type, event, session_id, payload_msg 等字段
    """
    if isinstance(res, str):
        logger.warning("Received string response instead of bytes")
        return {}

    if len(res) < 4:
        logger.warning(f"Response too short: {len(res)} bytes")
        return {}

    # 解析头部
    _ = res[0] >> 4  # protocol_version (unused)
    header_size = res[0] & 0x0F
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0F
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0F
    _ = res[3]  # reserved (unused)

    payload = res[header_size * 4:]
    result: dict[str, Any] = {}
    payload_msg: Any = None
    start = 0

    if message_type == SERVER_FULL_RESPONSE or message_type == SERVER_ACK:
        if message_type == SERVER_FULL_RESPONSE:
            result['message_type'] = 'SERVER_FULL_RESPONSE'
        else:
            result['message_type'] = 'SERVER_ACK'

        # 解析 sequence（如果有）
        if message_type_specific_flags & NEG_SEQUENCE > 0:
            result['seq'] = int.from_bytes(payload[:4], "big", signed=False)
            start += 4

        # 解析 event（如果有）
        if message_type_specific_flags & MSG_WITH_EVENT > 0:
            result['event'] = int.from_bytes(payload[:4], "big", signed=False)
            start += 4

        payload = payload[start:]

        # 解析 session_id
        if len(payload) >= 4:
            session_id_size = int.from_bytes(payload[:4], "big", signed=True)
            if session_id_size > 0 and len(payload) >= 4 + session_id_size:
                session_id = payload[4:session_id_size + 4]
                result['session_id'] = session_id.decode('utf-8', errors='ignore')
                payload = payload[4 + session_id_size:]

        # 解析 payload size 和 payload
        if len(payload) >= 4:
            payload_size = int.from_bytes(payload[:4], "big", signed=False)
            payload_msg = payload[4:]
            result['payload_size'] = payload_size

    elif message_type == SERVER_ERROR_RESPONSE:
        result['message_type'] = 'SERVER_ERROR'
        if len(payload) >= 4:
            code = int.from_bytes(payload[:4], "big", signed=False)
            result['code'] = code
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
            result['payload_size'] = payload_size
    else:
        logger.debug(f"Unknown message type: {message_type}")
        return result

    # 解压缩和反序列化 payload
    if payload_msg is not None and len(payload_msg) > 0:
        try:
            if message_compression == GZIP_COMPRESSION:
                payload_msg = gzip.decompress(payload_msg)

            if serialization_method == JSON_SERIALIZATION:
                payload_msg = json.loads(payload_msg.decode('utf-8'))
            elif serialization_method == NO_SERIALIZATION:
                # 保持为二进制（音频数据）
                pass
            else:
                payload_msg = payload_msg.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Failed to parse payload: {e}")

    result['payload_msg'] = payload_msg
    return result


def get_event_name(event_id: int) -> str:
    """获取事件名称（用于日志）."""
    event_names = {
        EVENT_CONNECTION_STARTED: "ConnectionStarted",
        EVENT_CONNECTION_FAILED: "ConnectionFailed",
        EVENT_CONNECTION_FINISHED: "ConnectionFinished",
        EVENT_SESSION_STARTED: "SessionStarted",
        EVENT_SESSION_FINISHED: "SessionFinished",
        EVENT_SESSION_FAILED: "SessionFailed",
        EVENT_USAGE_RESPONSE: "UsageResponse",
        EVENT_TTS_SENTENCE_START: "TTSSentenceStart",
        EVENT_TTS_SENTENCE_END: "TTSSentenceEnd",
        EVENT_TTS_RESPONSE: "TTSResponse",
        EVENT_TTS_ENDED: "TTSEnded",
        EVENT_ASR_INFO: "ASRInfo",
        EVENT_ASR_RESPONSE: "ASRResponse",
        EVENT_ASR_ENDED: "ASREnded",
        EVENT_CHAT_RESPONSE: "ChatResponse",
        EVENT_CHAT_TEXT_QUERY_CONFIRMED: "ChatTextQueryConfirmed",
        EVENT_CHAT_ENDED: "ChatEnded",
        EVENT_DIALOG_COMMON_ERROR: "DialogCommonError",
    }
    return event_names.get(event_id, f"UnknownEvent({event_id})")
