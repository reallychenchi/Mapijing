"""WebSocket 消息类型定义."""

from enum import Enum

from pydantic import BaseModel


class ClientMessageType(str, Enum):
    """客户端发送的消息类型."""

    AUDIO_DATA = "audio_data"
    AUDIO_END = "audio_end"
    INTERRUPT = "interrupt"


class ServerMessageType(str, Enum):
    """服务端发送的消息类型."""

    ASR_RESULT = "asr_result"
    ASR_END = "asr_end"
    TTS_CHUNK = "tts_chunk"
    TTS_END = "tts_end"
    EMOTION = "emotion"
    ERROR = "error"
    LLM_RESPONSE = "llm_response"  # 阶段4临时消息类型，阶段5将替换为tts_chunk


class ErrorCode(str, Enum):
    """错误码枚举."""

    ASR_ERROR = "ASR_ERROR"
    LLM_ERROR = "LLM_ERROR"
    TTS_ERROR = "TTS_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class EmotionType(str, Enum):
    """情感类型枚举."""

    DEFAULT = "默认陪伴"
    EMPATHY = "共情倾听"
    COMFORT = "安慰支持"
    HAPPY = "轻松愉悦"


# 服务端发送的消息数据模型
class AsrResultData(BaseModel):
    """ASR 识别结果数据."""

    text: str
    is_final: bool


class AsrEndData(BaseModel):
    """ASR 识别完成数据."""

    text: str


class TtsChunkData(BaseModel):
    """TTS 片段数据."""

    text: str
    audio: str  # base64
    seq: int
    is_final: bool


class TtsEndData(BaseModel):
    """TTS 完成数据."""

    full_text: str


class EmotionData(BaseModel):
    """情感状态数据."""

    emotion: EmotionType


class ErrorData(BaseModel):
    """错误数据."""

    code: ErrorCode
    message: str


# 服务端消息
class ServerMessage(BaseModel):
    """服务端消息."""

    type: ServerMessageType
    data: AsrResultData | AsrEndData | TtsChunkData | TtsEndData | EmotionData | ErrorData
    timestamp: int | None = None
