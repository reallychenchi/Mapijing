"""豆包端到端实时语音大模型 WebSocket 客户端.

该模块负责与火山引擎端到端语音API建立WebSocket连接，
处理二进制协议通信，发送音频/文本数据并接收响应。
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed

from .config import E2EConfig
from .protocol import (
    EVENT_CHAT_TEXT_QUERY,
    EVENT_FINISH_CONNECTION,
    EVENT_FINISH_SESSION,
    EVENT_SAY_HELLO,
    EVENT_START_CONNECTION,
    EVENT_START_SESSION,
    EVENT_TASK_REQUEST,
    build_audio_frame,
    build_event_frame,
    get_event_name,
    parse_response,
)

logger = logging.getLogger(__name__)


class E2EDialogClient:
    """端到端实时语音对话客户端.

    负责与火山引擎端到端语音API建立WebSocket连接，
    处理音频流的发送和响应的接收。
    """

    def __init__(
        self,
        config: E2EConfig,
        session_id: str,
        on_response: Callable[[dict[str, Any]], None],
        on_error: Callable[[str, bool], None],
    ) -> None:
        """初始化客户端.

        Args:
            config: 服务配置
            session_id: 会话ID
            on_response: 响应回调函数 (response_dict)
            on_error: 错误回调函数 (error_message, is_fatal)
        """
        self.config = config
        self.session_id = session_id
        self.on_response = on_response
        self.on_error = on_error

        self._connect_id = str(uuid.uuid4())
        self._ws: ClientConnection | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._connected = False
        self._session_started = False
        self._logid = ""

    @property
    def is_connected(self) -> bool:
        """检查是否已连接."""
        return self._connected and self._ws is not None

    @property
    def is_session_started(self) -> bool:
        """检查会话是否已启动."""
        return self._session_started

    @property
    def logid(self) -> str:
        """获取服务端日志ID（用于问题排查）."""
        return self._logid

    async def connect(self) -> bool:
        """连接到火山引擎端到端语音服务.

        Returns:
            连接是否成功
        """
        if self._connected:
            logger.debug("Already connected")
            return True

        headers = self.config.get_ws_headers(self._connect_id)
        logger.info(f"Connecting to E2E service: {self.config.base_url}")
        logger.debug(
            f"Connection headers: app_id={self.config.app_id}, "
            f"connect_id={self._connect_id}"
        )

        try:
            self._ws = await websockets.connect(
                self.config.base_url,
                additional_headers=headers,
                ping_interval=None,  # 服务端不支持 ping/pong
            )
            # websockets 16.0+ 使用 response.headers
            if hasattr(self._ws, 'response') and self._ws.response:
                self._logid = self._ws.response.headers.get("X-Tt-Logid", "")
            else:
                self._logid = ""
            logger.info(f"E2E WebSocket connected, logid={self._logid}")
            self._connected = True

            # 发送 StartConnection
            await self._send_start_connection()

            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_loop())

            return True

        except Exception as e:
            logger.error(f"E2E connection failed: {e}")
            self.on_error(f"E2E 连接失败: {e}", True)
            return False

    async def _send_start_connection(self) -> None:
        """发送 StartConnection 事件."""
        if not self._ws:
            return

        frame = build_event_frame(
            event_id=EVENT_START_CONNECTION,
            session_id="",
            payload={},
        )
        await self._ws.send(frame)
        logger.debug("StartConnection sent")

    async def start_session(self, input_mod: str = "audio") -> bool:
        """启动会话.

        Args:
            input_mod: 输入模式 (audio, text, audio_file, keep_alive)

        Returns:
            会话是否启动成功
        """
        if not self._connected or not self._ws:
            logger.error("Cannot start session: not connected")
            return False

        if self._session_started:
            logger.debug("Session already started")
            return True

        payload = self.config.get_start_session_payload(input_mod)
        frame = build_event_frame(
            event_id=EVENT_START_SESSION,
            session_id=self.session_id,
            payload=payload,
        )
        await self._ws.send(frame)
        logger.info(f"StartSession sent, session_id={self.session_id}, input_mod={input_mod}")
        return True

    async def send_audio(self, audio_data: bytes) -> None:
        """发送音频数据.

        Args:
            audio_data: PCM 格式音频数据 (16kHz, 16bit, mono)
        """
        if not self._ws or not self._connected:
            logger.warning("Cannot send audio: not connected")
            return

        if not self._session_started:
            logger.warning("Cannot send audio: session not started")
            return

        frame = build_audio_frame(
            event_id=EVENT_TASK_REQUEST,
            session_id=self.session_id,
            audio_data=audio_data,
        )
        await self._ws.send(frame)
        logger.debug(f"Audio sent: {len(audio_data)} bytes")

    async def send_text_query(self, text: str) -> None:
        """发送文本查询.

        Args:
            text: 用户输入的文本
        """
        if not self._ws or not self._connected:
            logger.warning("Cannot send text query: not connected")
            return

        if not self._session_started:
            logger.warning("Cannot send text query: session not started")
            return

        payload = {"content": text}
        frame = build_event_frame(
            event_id=EVENT_CHAT_TEXT_QUERY,
            session_id=self.session_id,
            payload=payload,
        )
        await self._ws.send(frame)
        logger.info(f"TextQuery sent: {text[:50]}...")

    async def say_hello(self, content: str = "你好，我是小马，有什么可以帮助你的吗？") -> None:
        """发送打招呼消息.

        Args:
            content: 打招呼的文本内容
        """
        if not self._ws or not self._connected:
            logger.warning("Cannot say hello: not connected")
            return

        if not self._session_started:
            logger.warning("Cannot say hello: session not started")
            return

        payload = {"content": content}
        frame = build_event_frame(
            event_id=EVENT_SAY_HELLO,
            session_id=self.session_id,
            payload=payload,
        )
        await self._ws.send(frame)
        logger.info(f"SayHello sent: {content[:30]}...")

    async def finish_session(self) -> None:
        """结束会话（保持WebSocket连接）."""
        if not self._ws or not self._connected:
            return

        frame = build_event_frame(
            event_id=EVENT_FINISH_SESSION,
            session_id=self.session_id,
            payload={},
        )
        await self._ws.send(frame)
        self._session_started = False
        logger.info("FinishSession sent")

    async def finish_connection(self) -> None:
        """结束连接."""
        if not self._ws or not self._connected:
            return

        # FinishConnection 是 Connection 级别事件，不带 session_id
        import gzip

        from .protocol import generate_header

        frame = bytearray(generate_header())
        frame.extend(EVENT_FINISH_CONNECTION.to_bytes(4, 'big'))
        payload_bytes = gzip.compress(b'{}')
        frame.extend(len(payload_bytes).to_bytes(4, 'big'))
        frame.extend(payload_bytes)

        await self._ws.send(frame)
        logger.info("FinishConnection sent")

    async def _receive_loop(self) -> None:
        """接收服务端响应的循环."""
        if not self._ws:
            return

        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    response = parse_response(message)
                    if response:
                        self._handle_response(response)
                else:
                    logger.warning(f"Received non-binary message: {type(message)}")

        except ConnectionClosed as e:
            logger.info(f"E2E connection closed: code={e.code}, reason={e.reason}")
            self._connected = False
            self._session_started = False
        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
        except Exception as e:
            logger.error(f"E2E receive error: {e}")
            self.on_error(f"E2E 接收错误: {e}", True)
        finally:
            self._connected = False
            self._session_started = False

    def _handle_response(self, response: dict[str, Any]) -> None:
        """处理服务端响应.

        Args:
            response: 解析后的响应字典
        """
        event = response.get('event')
        message_type = response.get('message_type')
        payload = response.get('payload_msg')

        # 记录事件日志
        if event:
            event_name = get_event_name(event)
            if event in (150, 152, 153, 450, 459, 350, 359, 550, 559):
                logger.info(f"E2E event: {event_name} ({event})")
            else:
                logger.debug(f"E2E event: {event_name} ({event})")

        # 处理会话状态
        if event == 150:  # SessionStarted
            self._session_started = True
            dialog_id = payload.get('dialog_id', '') if isinstance(payload, dict) else ''
            logger.info(f"Session started, dialog_id={dialog_id}")
        elif event == 152:  # SessionFinished
            self._session_started = False
            logger.info("Session finished")
        elif event == 153:  # SessionFailed
            self._session_started = False
            if isinstance(payload, dict):
                error_msg = payload.get('error', 'Unknown error')
            else:
                error_msg = 'Session failed'
            logger.error(f"Session failed: {error_msg}")
            self.on_error(error_msg, True)
            return

        # 处理错误
        if message_type == 'SERVER_ERROR':
            if isinstance(payload, dict):
                error_msg = payload.get('error', 'Unknown error')
            else:
                error_msg = str(payload)
            logger.error(f"Server error: {error_msg}")
            self.on_error(error_msg, False)
            return

        if event == 599:  # DialogCommonError
            error_info = payload if isinstance(payload, dict) else {}
            status_code = error_info.get('status_code', 'unknown')
            message = error_info.get('message', 'Dialog error')
            logger.error(f"Dialog error: {status_code} - {message}")
            self.on_error(f"{status_code}: {message}", False)
            return

        # 转发响应到回调
        self.on_response(response)

    async def close(self) -> None:
        """关闭连接."""
        self._connected = False
        self._session_started = False

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
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            self._ws = None

        logger.info(f"E2E client closed, logid={self._logid}")
