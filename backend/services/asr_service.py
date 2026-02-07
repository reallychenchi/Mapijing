"""火山引擎 ASR 代理服务."""

import asyncio
import base64
import logging
import uuid
from collections.abc import Callable

import websockets
from websockets import ClientConnection
from websockets.exceptions import ConnectionClosed

from config.settings import settings
from utils.protocol import (
    build_audio_only_request,
    build_full_client_request,
    parse_response,
)

logger = logging.getLogger(__name__)


class ASRService:
    """火山引擎 ASR 代理服务.

    负责与火山引擎 ASR 服务建立 WebSocket 连接，
    转发音频数据并接收识别结果。
    """

    def __init__(
        self,
        on_result: Callable[[str, bool], None],
        on_error: Callable[[str], None],
    ) -> None:
        """初始化 ASR 服务.

        Args:
            on_result: 识别结果回调 (text, is_final)
            on_error: 错误回调 (error_message)
        """
        self.on_result = on_result
        self.on_error = on_error
        self._ws: ClientConnection | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._connected = False
        self._session_id = ""
        self._seq = 0

    @property
    def is_connected(self) -> bool:
        """检查是否已连接."""
        return self._connected and self._ws is not None

    async def connect(self) -> bool:
        """连接到火山引擎 ASR 服务."""
        if self._connected:
            return True

        self._session_id = str(uuid.uuid4())
        self._seq = 0

        # 构建认证头
        headers = {
            "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
            "X-Api-Access-Key": settings.VOLC_ASR_ACCESS_KEY,
            "X-Api-App-Key": settings.VOLC_ASR_APP_ID,
            "X-Api-Request-Id": self._session_id,
        }

        try:
            self._ws = await websockets.connect(
                settings.VOLC_ASR_URL,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
            )
            self._connected = True
            logger.info(f"ASR connected, session_id={self._session_id}")

            # 发送初始配置
            await self._send_config()

            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_loop())

            return True
        except Exception as e:
            logger.error(f"ASR connection failed: {e}")
            self.on_error(f"ASR 连接失败: {e}")
            return False

    async def _send_config(self) -> None:
        """发送初始配置请求."""
        if not self._ws:
            return

        config = {
            "user": {
                "uid": self._session_id,
            },
            "audio": {
                "format": "pcm",
                "sample_rate": 16000,
                "bits": 16,
                "channel": 1,
                "codec": "raw",
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "result_type": "single",
            },
        }

        frame = build_full_client_request(config)
        await self._ws.send(frame)
        logger.debug("ASR config sent")

    async def send_audio(self, audio_base64: str, seq: int, is_last: bool = False) -> None:
        """发送音频数据.

        Args:
            audio_base64: Base64 编码的音频数据
            seq: 序列号
            is_last: 是否为最后一帧
        """
        if not self._ws or not self._connected:
            logger.warning("ASR not connected, audio dropped")
            return

        try:
            audio_data = base64.b64decode(audio_base64)
            frame = build_audio_only_request(audio_data, seq, is_last)
            await self._ws.send(frame)
            self._seq = seq
            logger.debug(f"ASR audio sent, seq={seq}, is_last={is_last}, size={len(audio_data)}")
        except Exception as e:
            logger.error(f"ASR send audio failed: {e}")

    async def _receive_loop(self) -> None:
        """接收服务端响应的循环."""
        if not self._ws:
            return

        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    result = parse_response(message)
                    if result:
                        if result.get("error"):
                            error_msg = result.get("message", "Unknown ASR error")
                            logger.error(f"ASR error: {error_msg}")
                            self.on_error(error_msg)
                        else:
                            text = result.get("text", "")
                            is_final = result.get("is_final", False)
                            if text:
                                logger.debug(f"ASR result: {text}, is_final={is_final}")
                                self.on_result(text, is_final)
        except ConnectionClosed:
            logger.info("ASR connection closed")
        except Exception as e:
            logger.error(f"ASR receive error: {e}")
            self.on_error(f"ASR 接收错误: {e}")
        finally:
            self._connected = False

    async def disconnect(self) -> None:
        """断开连接."""
        self._connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        logger.info("ASR disconnected")
