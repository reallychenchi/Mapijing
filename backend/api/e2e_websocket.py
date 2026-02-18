"""端到端实时语音对话 WebSocket 端点实现."""

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from config.settings import settings
from models.message import ErrorCode, ServerMessageType
from services.e2e import E2EConfig, E2EDialogService

logger = logging.getLogger(__name__)


class E2EConnectionManager:
    """端到端 WebSocket 连接管理器."""

    def __init__(self) -> None:
        """初始化连接管理器."""
        self.active_connection: WebSocket | None = None
        self.e2e_service: E2EDialogService | None = None
        self._receive_task: asyncio.Task[None] | None = None

    async def connect(self, websocket: WebSocket) -> None:
        """接受并存储连接."""
        await websocket.accept()
        self.active_connection = websocket

        # 初始化端到端服务
        config = E2EConfig(
            app_id=settings.VOLC_E2E_APP_ID,
            access_key=settings.VOLC_E2E_ACCESS_KEY,
            model=settings.VOLC_E2E_MODEL,
            speaker=settings.VOLC_E2E_SPEAKER,
            bot_name=settings.VOLC_E2E_BOT_NAME,
            system_role=settings.VOLC_E2E_SYSTEM_ROLE,
            speaking_style=settings.VOLC_E2E_SPEAKING_STYLE,
        )
        self.e2e_service = E2EDialogService(config)

        logger.info("E2E WebSocket client connected")

    async def disconnect(self) -> None:
        """断开连接."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self.e2e_service:
            await self.e2e_service.close()
            self.e2e_service = None

        self.active_connection = None
        logger.info("E2E WebSocket disconnected")

    async def send_message(self, message: dict[str, Any]) -> None:
        """发送消息到前端."""
        if self.active_connection:
            if "timestamp" not in message:
                message["timestamp"] = int(time.time() * 1000)
            await self.active_connection.send_json(message)

    async def send_error(self, code: ErrorCode, message: str) -> None:
        """发送错误消息."""
        logger.error(f"E2E error [{code.value}]: {message}")
        await self.send_message({
            "type": ServerMessageType.ERROR.value,
            "data": {"code": code.value, "message": message},
        })

    async def send_asr_result(self, text: str, is_final: bool) -> None:
        """发送 ASR 识别结果."""
        await self.send_message({
            "type": ServerMessageType.ASR_RESULT.value,
            "data": {"text": text, "is_final": is_final},
        })

    async def send_asr_end(self, text: str = "") -> None:
        """发送 ASR 识别完成消息."""
        await self.send_message({
            "type": ServerMessageType.ASR_END.value,
            "data": {"text": text},
        })

    async def send_tts_chunk(self, audio: str, text: str = "", seq: int = 0) -> None:
        """发送 TTS 音频片段."""
        await self.send_message({
            "type": ServerMessageType.TTS_CHUNK.value,
            "data": {"text": text, "audio": audio, "seq": seq, "is_final": False},
        })

    async def send_tts_end(self, full_text: str = "") -> None:
        """发送 TTS 完成消息."""
        await self.send_message({
            "type": ServerMessageType.TTS_END.value,
            "data": {"full_text": full_text},
        })

    async def send_chat_text(self, text: str) -> None:
        """发送对话文本（流式）."""
        await self.send_message({
            "type": "chat_text",
            "data": {"text": text},
        })

    async def start_e2e_session(self, input_mod: str = "audio") -> bool:
        """启动端到端会话.

        Args:
            input_mod: 输入模式 (audio, text)

        Returns:
            会话是否启动成功
        """
        if not self.e2e_service:
            await self.send_error(ErrorCode.UNKNOWN_ERROR, "E2E 服务未初始化")
            return False

        # 连接到火山引擎服务
        connected = await self.e2e_service.connect()
        if not connected:
            await self.send_error(ErrorCode.NETWORK_ERROR, "连接端到端语音服务失败")
            return False

        # 启动会话
        started = await self.e2e_service.start_session(input_mod)
        if not started:
            await self.send_error(ErrorCode.NETWORK_ERROR, "启动端到端会话失败")
            return False

        # 启动响应接收任务
        self._receive_task = asyncio.create_task(self._receive_responses())

        logger.info(f"E2E session started, session_id={self.e2e_service.session_id}")
        await self.send_message({
            "type": "session_started",
            "data": {"session_id": self.e2e_service.session_id},
        })
        return True

    async def _receive_responses(self) -> None:
        """接收并转发端到端服务的响应."""
        if not self.e2e_service:
            return

        tts_seq = 0
        full_chat_text = ""

        try:
            async for response in self.e2e_service.receive_responses():
                resp_type = response.get("type")
                data = response.get("data", {})

                if resp_type == "asr_started":
                    # 用户开始说话，清空之前的状态
                    tts_seq = 0
                    full_chat_text = ""
                    logger.debug("ASR started (user speaking)")

                elif resp_type == "asr_result":
                    text = data.get("text", "")
                    is_final = data.get("is_final", False)
                    await self.send_asr_result(text, is_final)

                elif resp_type == "asr_ended":
                    await self.send_asr_end()

                elif resp_type == "chat_text":
                    text = data.get("text", "")
                    full_chat_text += text
                    await self.send_chat_text(text)

                elif resp_type == "chat_ended":
                    logger.debug(f"Chat ended, full text: {full_chat_text[:50]}...")

                elif resp_type == "tts_start":
                    tts_type = data.get("tts_type", "default")
                    logger.debug(f"TTS started, type={tts_type}")

                elif resp_type == "tts_chunk":
                    audio = data.get("audio", "")
                    if audio:
                        await self.send_tts_chunk(audio, seq=tts_seq)
                        tts_seq += 1

                elif resp_type == "tts_ended":
                    await self.send_tts_end(full_chat_text)
                    tts_seq = 0
                    full_chat_text = ""

                elif resp_type == "error":
                    error_msg = data.get("message", "未知错误")
                    is_fatal = data.get("is_fatal", False)
                    if is_fatal:
                        await self.send_error(ErrorCode.UNKNOWN_ERROR, error_msg)
                        return
                    else:
                        logger.warning(f"E2E non-fatal error: {error_msg}")

        except asyncio.CancelledError:
            logger.debug("Response receive task cancelled")
        except Exception as e:
            logger.error(f"Error receiving responses: {e}")
            await self.send_error(ErrorCode.UNKNOWN_ERROR, str(e))


# 全局连接管理器实例
e2e_manager = E2EConnectionManager()


async def handle_e2e_message(message: dict[str, Any], websocket: WebSocket) -> None:
    """处理前端消息."""
    msg_type = message.get("type")

    if msg_type == "start_session":
        # 启动会话
        data = message.get("data", {})
        input_mod = data.get("input_mod", "audio")
        await e2e_manager.start_e2e_session(input_mod)

    elif msg_type == "audio_data":
        # 音频数据
        data = message.get("data", {})
        audio = data.get("audio", "")
        if audio and e2e_manager.e2e_service:
            await e2e_manager.e2e_service.send_audio(audio)

    elif msg_type == "text_query":
        # 文本查询
        data = message.get("data", {})
        text = data.get("text", "")
        if text and e2e_manager.e2e_service:
            await e2e_manager.e2e_service.send_text(text)

    elif msg_type == "say_hello":
        # 打招呼
        data = message.get("data", {})
        content = data.get("content")
        if e2e_manager.e2e_service:
            await e2e_manager.e2e_service.say_hello(content)

    elif msg_type == "interrupt":
        # 打断
        if e2e_manager.e2e_service:
            e2e_manager.e2e_service.interrupt()
            await e2e_manager.send_tts_end("")

    elif msg_type == "finish_session":
        # 结束会话
        if e2e_manager.e2e_service:
            await e2e_manager.e2e_service.finish_session()

    else:
        logger.warning(f"Unknown message type: {msg_type}")
        await e2e_manager.send_error(
            ErrorCode.UNKNOWN_ERROR, f"未知消息类型: {msg_type}"
        )


async def e2e_websocket_endpoint(websocket: WebSocket) -> None:
    """端到端 WebSocket 端点处理函数."""
    await e2e_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_e2e_message(message, websocket)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                await e2e_manager.send_error(
                    ErrorCode.UNKNOWN_ERROR, f"无效的 JSON 格式: {e}"
                )
    except WebSocketDisconnect:
        await e2e_manager.disconnect()
    except Exception as e:
        logger.error(f"E2E WebSocket error: {e}")
        try:
            await e2e_manager.send_error(ErrorCode.UNKNOWN_ERROR, str(e))
        except Exception:
            pass
        await e2e_manager.disconnect()
