"""火山引擎 TTS 服务."""

import gzip
import io
import json
import logging
import struct
import uuid
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import websockets
from websockets import ClientConnection

from config.settings import settings

logger = logging.getLogger(__name__)


class MsgType(IntEnum):
    """消息类型枚举."""

    INVALID = 0
    FULL_CLIENT_REQUEST = 0b0001
    AUDIO_ONLY_CLIENT = 0b0010
    FULL_SERVER_RESPONSE = 0b1001
    AUDIO_ONLY_SERVER = 0b1011
    FRONTEND_RESULT_SERVER = 0b1100
    ERROR = 0b1111


class MsgTypeFlagBits(IntEnum):
    """消息类型标志位."""

    NO_SEQ = 0
    POSITIVE_SEQ = 0b0001
    LAST_NO_SEQ = 0b0010
    NEGATIVE_SEQ = 0b0011
    WITH_EVENT = 0b0100


class SerializationBits(IntEnum):
    """序列化方式."""

    RAW = 0
    JSON = 0b0001


class CompressionBits(IntEnum):
    """压缩方式."""

    NONE = 0
    GZIP = 0b0001


@dataclass
class TTSConfig:
    """TTS 配置."""

    app_id: str = ""
    access_key: str = ""  # Bearer token
    cluster: str = "volcano_tts"
    voice_type: str = "zh_female_cancan_mars_bigtts"
    encoding: str = "mp3"
    speed_ratio: float = 1.0
    volume_ratio: float = 1.0
    pitch_ratio: float = 1.0


@dataclass
class TTSResult:
    """TTS 结果."""

    audio_data: bytes  # MP3 音频二进制
    duration_ms: int  # 估算音频时长（毫秒）
    success: bool
    error_message: str | None = None


class TTSMessage:
    """TTS 二进制协议消息."""

    VERSION = 0b0001
    HEADER_SIZE = 0b0001

    def __init__(
        self,
        msg_type: MsgType = MsgType.INVALID,
        flag: MsgTypeFlagBits = MsgTypeFlagBits.NO_SEQ,
        serialization: SerializationBits = SerializationBits.JSON,
        compression: CompressionBits = CompressionBits.NONE,
    ) -> None:
        """初始化消息."""
        self.msg_type = msg_type
        self.flag = flag
        self.serialization = serialization
        self.compression = compression
        self.sequence: int = 0
        self.error_code: int = 0
        self.payload: bytes = b""

    def marshal(self) -> bytes:
        """序列化消息为字节."""
        buffer = io.BytesIO()

        # 写入头部 (4 bytes)
        header = [
            (self.VERSION << 4) | self.HEADER_SIZE,
            (self.msg_type << 4) | self.flag,
            (self.serialization << 4) | self.compression,
            0x00,  # reserved
        ]
        buffer.write(bytes(header))

        # 写入序列号（如果需要）
        if self.flag in [MsgTypeFlagBits.POSITIVE_SEQ, MsgTypeFlagBits.NEGATIVE_SEQ]:
            buffer.write(struct.pack(">i", self.sequence))

        # 写入 payload 大小和数据
        buffer.write(struct.pack(">I", len(self.payload)))
        buffer.write(self.payload)

        return buffer.getvalue()

    @classmethod
    def unmarshal(cls, data: bytes) -> "TTSMessage":
        """从字节反序列化消息."""
        if len(data) < 4:
            raise ValueError(f"Data too short: expected at least 4 bytes, got {len(data)}")

        msg = cls()

        # 解析头部
        msg.msg_type = MsgType((data[1] >> 4) & 0x0F)
        msg.flag = MsgTypeFlagBits(data[1] & 0x0F)
        msg.serialization = SerializationBits((data[2] >> 4) & 0x0F)
        msg.compression = CompressionBits(data[2] & 0x0F)

        cursor = 4

        # 读取序列号（如果有）
        if msg.flag in [MsgTypeFlagBits.POSITIVE_SEQ, MsgTypeFlagBits.NEGATIVE_SEQ]:
            if len(data) >= cursor + 4:
                msg.sequence = struct.unpack(">i", data[cursor : cursor + 4])[0]
                cursor += 4

        # 读取错误码（如果是错误消息）
        if msg.msg_type == MsgType.ERROR:
            if len(data) >= cursor + 4:
                msg.error_code = struct.unpack(">I", data[cursor : cursor + 4])[0]
                cursor += 4

        # 读取 payload
        if len(data) >= cursor + 4:
            payload_size = struct.unpack(">I", data[cursor : cursor + 4])[0]
            cursor += 4
            if payload_size > 0 and len(data) >= cursor + payload_size:
                msg.payload = data[cursor : cursor + payload_size]

        return msg

    def __str__(self) -> str:
        """字符串表示."""
        if self.msg_type == MsgType.AUDIO_ONLY_SERVER:
            return (
                f"MsgType: {self.msg_type.name}, Seq: {self.sequence}, "
                f"PayloadSize: {len(self.payload)}"
            )
        if self.msg_type == MsgType.ERROR:
            return f"MsgType: {self.msg_type.name}, ErrorCode: {self.error_code}"
        return f"MsgType: {self.msg_type.name}, PayloadSize: {len(self.payload)}"


def get_cluster(voice_type: str) -> str:
    """根据音色类型获取集群."""
    if voice_type.startswith("S_"):
        return "volcano_icl"
    return "volcano_tts"


class TTSService:
    """火山引擎 TTS 服务."""

    WS_URL = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"

    def __init__(self, config: TTSConfig | None = None) -> None:
        """初始化 TTS 服务.

        Args:
            config: TTS 配置，如果为 None 则使用默认配置
        """
        if config is None:
            config = TTSConfig(
                app_id=settings.VOLC_TTS_APP_ID,
                access_key=settings.VOLC_TTS_ACCESS_KEY,
                cluster=settings.VOLC_TTS_CLUSTER,
            )
        self.config = config

    async def synthesize(self, text: str) -> TTSResult:
        """合成单句语音.

        Args:
            text: 要合成的文字

        Returns:
            TTSResult 对象
        """
        if not text.strip():
            return TTSResult(
                audio_data=b"",
                duration_ms=0,
                success=True,
            )

        try:
            audio_chunks: list[bytes] = []

            headers = {
                "Authorization": f"Bearer;{self.config.access_key}",
            }

            async with websockets.connect(
                self.WS_URL,
                additional_headers=headers,
                max_size=10 * 1024 * 1024,
            ) as ws:
                # 发送请求
                await self._send_request(ws, text)

                # 接收响应
                while True:
                    response = await ws.recv()
                    if isinstance(response, bytes):
                        result = self._parse_response(response)

                        if result.get("error"):
                            return TTSResult(
                                audio_data=b"",
                                duration_ms=0,
                                success=False,
                                error_message=result.get("message", "Unknown TTS error"),
                            )

                        if result.get("audio"):
                            audio_chunks.append(result["audio"])

                        if result.get("is_last"):
                            break
                    else:
                        logger.warning(f"Unexpected text message: {response}")

            # 合并音频
            full_audio = b"".join(audio_chunks)

            return TTSResult(
                audio_data=full_audio,
                duration_ms=self._estimate_duration(len(full_audio)),
                success=True,
            )

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return TTSResult(
                audio_data=b"",
                duration_ms=0,
                success=False,
                error_message=str(e),
            )

    async def _send_request(self, ws: ClientConnection, text: str) -> None:
        """发送 TTS 请求."""
        # 确定 cluster
        cluster = get_cluster(self.config.voice_type)
        if self.config.cluster:
            cluster = self.config.cluster

        request_json: dict[str, Any] = {
            "app": {
                "appid": self.config.app_id,
                "token": self.config.access_key,
                "cluster": cluster,
            },
            "user": {
                "uid": f"user_{uuid.uuid4().hex[:8]}",
            },
            "audio": {
                "voice_type": self.config.voice_type,
                "encoding": self.config.encoding,
                "rate": 24000,
                "speed_ratio": self.config.speed_ratio,
                "volume_ratio": self.config.volume_ratio,
                "pitch_ratio": self.config.pitch_ratio,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "submit",
                "with_timestamp": 1,
            },
        }

        payload = json.dumps(request_json).encode("utf-8")

        # 构建消息
        msg = TTSMessage(
            msg_type=MsgType.FULL_CLIENT_REQUEST,
            flag=MsgTypeFlagBits.NO_SEQ,
            serialization=SerializationBits.JSON,
            compression=CompressionBits.GZIP,
        )
        msg.payload = gzip.compress(payload)

        await ws.send(msg.marshal())
        logger.debug(f"TTS request sent: {text[:50]}...")

    def _parse_response(self, data: bytes) -> dict[str, Any]:
        """解析 TTS 响应."""
        result: dict[str, Any] = {}

        try:
            msg = TTSMessage.unmarshal(data)

            if msg.msg_type == MsgType.AUDIO_ONLY_SERVER:
                # 音频数据
                audio_data = msg.payload
                if msg.compression == CompressionBits.GZIP and audio_data:
                    try:
                        audio_data = gzip.decompress(audio_data)
                    except Exception:
                        pass  # 可能不是 gzip 压缩的
                result["audio"] = audio_data

                # 检查是否是最后一帧
                if msg.flag in [MsgTypeFlagBits.LAST_NO_SEQ, MsgTypeFlagBits.NEGATIVE_SEQ]:
                    result["is_last"] = True

            elif msg.msg_type == MsgType.FULL_SERVER_RESPONSE:
                # 解析 JSON 响应
                payload = msg.payload
                if msg.compression == CompressionBits.GZIP and payload:
                    try:
                        payload = gzip.decompress(payload)
                    except Exception:
                        pass

                try:
                    response = json.loads(payload.decode("utf-8"))
                    # 检查是否有音频数据
                    if "data" in response:
                        import base64

                        audio_b64 = response.get("data", "")
                        if audio_b64:
                            result["audio"] = base64.b64decode(audio_b64)
                except Exception:
                    pass

            elif msg.msg_type == MsgType.ERROR:
                error_msg = "TTS error"
                if msg.payload:
                    try:
                        payload = msg.payload
                        if msg.compression == CompressionBits.GZIP:
                            payload = gzip.decompress(payload)
                        error_json = json.loads(payload.decode("utf-8"))
                        error_msg = error_json.get("message", str(error_json))
                    except Exception:
                        error_msg = msg.payload.decode("utf-8", errors="ignore")
                result["error"] = True
                result["message"] = error_msg
                logger.error(f"TTS error: code={msg.error_code}, msg={error_msg}")

            elif msg.msg_type == MsgType.FRONTEND_RESULT_SERVER:
                # 前端结果消息，可能表示完成
                result["is_last"] = True

        except Exception as e:
            logger.error(f"TTS parse error: {e}")
            result["error"] = True
            result["message"] = str(e)

        return result

    def _estimate_duration(self, audio_size: int) -> int:
        """估算音频时长（毫秒）.

        基于 MP3 128kbps 的假设：16KB/s
        """
        if audio_size == 0:
            return 0
        return int(audio_size / 16 * 1000)
