"""端到端实时语音对话服务.

该模块提供面向上层API的端到端语音对话服务接口，
封装了与火山引擎端到端语音API的通信细节。
"""

import asyncio
import base64
import logging
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from .client import E2EDialogClient
from .config import E2EConfig
from .protocol import (
    EVENT_ASR_ENDED,
    EVENT_ASR_INFO,
    EVENT_ASR_RESPONSE,
    EVENT_CHAT_ENDED,
    EVENT_CHAT_RESPONSE,
    EVENT_SESSION_STARTED,
    EVENT_TTS_ENDED,
    EVENT_TTS_RESPONSE,
    EVENT_TTS_SENTENCE_START,
)

logger = logging.getLogger(__name__)


@dataclass
class ASRResult:
    """ASR 识别结果."""

    text: str
    is_interim: bool  # True 表示中间结果，False 表示最终结果


@dataclass
class TTSChunk:
    """TTS 音频片段."""

    text: str
    audio: bytes  # PCM 音频数据
    tts_type: str = "default"  # default, chat_tts_text, external_rag, etc.


@dataclass
class ChatResult:
    """对话文本结果."""

    text: str
    question_id: str = ""
    reply_id: str = ""


class E2EDialogService:
    """端到端实时语音对话服务.

    提供完整的端到端语音对话功能，包括：
    - 音频流式输入
    - ASR 实时识别结果
    - 模型生成的文本响应
    - TTS 音频流式输出
    """

    def __init__(self, config: E2EConfig) -> None:
        """初始化服务.

        Args:
            config: 服务配置
        """
        self.config = config
        self._client: E2EDialogClient | None = None
        self._session_id = ""

        # 响应队列
        self._response_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._error_queue: asyncio.Queue[tuple[str, bool]] = asyncio.Queue()

        # 状态标志
        self._is_user_speaking = False
        self._is_ai_responding = False
        self._interrupted = False

    @property
    def session_id(self) -> str:
        """获取当前会话ID."""
        return self._session_id

    @property
    def is_connected(self) -> bool:
        """检查是否已连接."""
        return self._client is not None and self._client.is_connected

    @property
    def is_session_started(self) -> bool:
        """检查会话是否已启动."""
        return self._client is not None and self._client.is_session_started

    async def connect(self) -> bool:
        """连接到端到端语音服务.

        Returns:
            连接是否成功
        """
        if self._client and self._client.is_connected:
            return True

        self._session_id = str(uuid.uuid4())
        self._response_queue = asyncio.Queue()
        self._error_queue = asyncio.Queue()

        self._client = E2EDialogClient(
            config=self.config,
            session_id=self._session_id,
            on_response=self._on_response,
            on_error=self._on_error,
        )

        success = await self._client.connect()
        if success:
            logger.info(f"E2E service connected, session_id={self._session_id}")
        return success

    async def start_session(self, input_mod: str = "audio") -> bool:
        """启动对话会话.

        Args:
            input_mod: 输入模式 (audio, text, audio_file, keep_alive)

        Returns:
            会话是否启动成功
        """
        if not self._client:
            logger.error("Cannot start session: not connected")
            return False

        success = await self._client.start_session(input_mod)
        if success:
            # 等待 SessionStarted 事件
            try:
                while True:
                    response = await asyncio.wait_for(
                        self._response_queue.get(), timeout=10.0
                    )
                    if response.get('event') == EVENT_SESSION_STARTED:
                        logger.info("Session started successfully")
                        return True
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for SessionStarted")
                return False

        return False

    async def send_audio(self, audio_base64: str) -> None:
        """发送音频数据.

        Args:
            audio_base64: Base64 编码的 PCM 音频数据
        """
        if not self._client or not self._client.is_session_started:
            logger.warning("Cannot send audio: session not ready")
            return

        try:
            audio_data = base64.b64decode(audio_base64)
            await self._client.send_audio(audio_data)
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")

    async def send_text(self, text: str) -> None:
        """发送文本查询.

        Args:
            text: 用户输入的文本
        """
        if not self._client or not self._client.is_session_started:
            logger.warning("Cannot send text: session not ready")
            return

        await self._client.send_text_query(text)

    async def say_hello(self, content: str | None = None) -> None:
        """发送打招呼消息.

        Args:
            content: 打招呼的文本内容（可选）
        """
        if not self._client or not self._client.is_session_started:
            logger.warning("Cannot say hello: session not ready")
            return

        if content:
            await self._client.say_hello(content)
        else:
            await self._client.say_hello()

    def interrupt(self) -> None:
        """中断当前响应."""
        self._interrupted = True
        self._is_ai_responding = False
        logger.info("Response interrupted")

    async def receive_responses(self) -> AsyncGenerator[dict[str, Any], None]:
        """接收服务端响应的异步生成器.

        Yields:
            响应字典，包含以下类型：
            - asr_result: ASR 识别结果
            - tts_chunk: TTS 音频片段
            - chat_text: 对话文本
            - asr_started: 用户开始说话
            - asr_ended: 用户说话结束
            - tts_ended: AI 回复结束
            - error: 错误信息
        """
        self._interrupted = False

        while True:
            # 检查错误队列
            try:
                error_msg, is_fatal = self._error_queue.get_nowait()
                yield {
                    "type": "error",
                    "data": {"message": error_msg, "is_fatal": is_fatal},
                }
                if is_fatal:
                    return
            except asyncio.QueueEmpty:
                pass

            # 获取响应
            try:
                response = await asyncio.wait_for(
                    self._response_queue.get(), timeout=0.1
                )
            except asyncio.TimeoutError:
                # 检查连接状态
                if not self.is_connected:
                    yield {
                        "type": "error",
                        "data": {"message": "连接已断开", "is_fatal": True},
                    }
                    return
                continue

            if self._interrupted:
                # 丢弃被打断后的响应
                continue

            # 解析并转换响应
            converted = self._convert_response(response)
            if converted:
                yield converted

    def _convert_response(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """转换服务端响应为统一格式.

        Args:
            response: 原始响应字典

        Returns:
            转换后的响应字典，或 None（如果不需要转发）
        """
        event = response.get('event')
        payload = response.get('payload_msg')
        message_type = response.get('message_type')

        # ASR 相关事件
        if event == EVENT_ASR_INFO:
            self._is_user_speaking = True
            question_id = payload.get('question_id', '') if isinstance(payload, dict) else ''
            return {
                "type": "asr_started",
                "data": {"question_id": question_id},
            }

        if event == EVENT_ASR_RESPONSE:
            if isinstance(payload, dict):
                results = payload.get('results', [])
                for result in results:
                    text = result.get('text', '')
                    is_interim = result.get('is_interim', True)
                    if text:
                        return {
                            "type": "asr_result",
                            "data": {"text": text, "is_final": not is_interim},
                        }
            return None

        if event == EVENT_ASR_ENDED:
            self._is_user_speaking = False
            return {"type": "asr_ended", "data": {}}

        # Chat 相关事件
        if event == EVENT_CHAT_RESPONSE:
            self._is_ai_responding = True
            if isinstance(payload, dict):
                content = payload.get('content', '')
                question_id = payload.get('question_id', '')
                reply_id = payload.get('reply_id', '')
                if content:
                    return {
                        "type": "chat_text",
                        "data": {
                            "text": content,
                            "question_id": question_id,
                            "reply_id": reply_id,
                        },
                    }
            return None

        if event == EVENT_CHAT_ENDED:
            return {
                "type": "chat_ended",
                "data": payload if isinstance(payload, dict) else {},
            }

        # TTS 相关事件
        if event == EVENT_TTS_SENTENCE_START:
            if isinstance(payload, dict):
                tts_type = payload.get('tts_type', 'default')
                text = payload.get('text', '')
                return {
                    "type": "tts_start",
                    "data": {"tts_type": tts_type, "text": text},
                }
            return None

        if event == EVENT_TTS_RESPONSE:
            # 音频数据
            if message_type == 'SERVER_ACK' and isinstance(payload, bytes):
                audio_base64 = base64.b64encode(payload).decode('utf-8')
                return {
                    "type": "tts_chunk",
                    "data": {"audio": audio_base64},
                }
            return None

        if event == EVENT_TTS_ENDED:
            self._is_ai_responding = False
            return {
                "type": "tts_ended",
                "data": payload if isinstance(payload, dict) else {},
            }

        return None

    def _on_response(self, response: dict[str, Any]) -> None:
        """响应回调.

        Args:
            response: 服务端响应
        """
        try:
            self._response_queue.put_nowait(response)
        except asyncio.QueueFull:
            logger.warning("Response queue full, dropping response")

    def _on_error(self, error_msg: str, is_fatal: bool) -> None:
        """错误回调.

        Args:
            error_msg: 错误信息
            is_fatal: 是否为致命错误
        """
        try:
            self._error_queue.put_nowait((error_msg, is_fatal))
        except asyncio.QueueFull:
            logger.warning("Error queue full, dropping error")

    async def finish_session(self) -> None:
        """结束当前会话."""
        if self._client:
            await self._client.finish_session()

    async def close(self) -> None:
        """关闭服务连接."""
        if self._client:
            try:
                await self._client.finish_session()
                await self._client.finish_connection()
            except Exception as e:
                logger.warning(f"Error during graceful shutdown: {e}")
            await self._client.close()
            self._client = None

        logger.info("E2E service closed")
