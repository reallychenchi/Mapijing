"""WebSocket 端点实现."""

import json
import logging
import time

from fastapi import WebSocket, WebSocketDisconnect

from models.message import ErrorCode, ServerMessageType
from services.asr_service import ASRService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器."""

    def __init__(self) -> None:
        """初始化连接管理器."""
        self.active_connection: WebSocket | None = None
        self.asr_service: ASRService | None = None
        self._final_text = ""

    async def connect(self, websocket: WebSocket) -> None:
        """接受并存储连接."""
        await websocket.accept()
        self.active_connection = websocket
        self._final_text = ""
        logger.info("WebSocket connected")

    async def disconnect(self) -> None:
        """断开连接."""
        if self.asr_service:
            await self.asr_service.disconnect()
            self.asr_service = None
        self.active_connection = None
        logger.info("WebSocket disconnected")

    async def send_message(self, message: dict[str, object]) -> None:
        """发送消息."""
        if self.active_connection:
            # 添加时间戳
            if "timestamp" not in message:
                message["timestamp"] = int(time.time() * 1000)
            await self.active_connection.send_json(message)

    async def send_error(self, code: ErrorCode, message: str) -> None:
        """发送错误消息."""
        await self.send_message(
            {
                "type": ServerMessageType.ERROR.value,
                "data": {"code": code.value, "message": message},
            }
        )

    async def send_asr_result(self, text: str, is_final: bool) -> None:
        """发送 ASR 识别结果."""
        if is_final:
            self._final_text = text
        await self.send_message(
            {
                "type": ServerMessageType.ASR_RESULT.value,
                "data": {"text": text, "is_final": is_final},
            }
        )

    async def send_asr_end(self) -> None:
        """发送 ASR 识别完成消息."""
        await self.send_message(
            {
                "type": ServerMessageType.ASR_END.value,
                "data": {"text": self._final_text},
            }
        )

    async def start_asr(self) -> bool:
        """启动 ASR 服务."""
        if self.asr_service and self.asr_service.is_connected:
            return True

        def on_result(text: str, is_final: bool) -> None:
            """ASR 结果回调."""
            import asyncio

            asyncio.create_task(self.send_asr_result(text, is_final))

        def on_error(error: str) -> None:
            """ASR 错误回调."""
            import asyncio

            asyncio.create_task(self.send_error(ErrorCode.ASR_ERROR, error))

        self.asr_service = ASRService(on_result=on_result, on_error=on_error)
        return await self.asr_service.connect()

    async def stop_asr(self) -> None:
        """停止 ASR 服务."""
        if self.asr_service:
            await self.asr_service.disconnect()
            self.asr_service = None


manager = ConnectionManager()


async def handle_message(message: dict[str, object], websocket: WebSocket) -> None:
    """消息路由处理."""
    msg_type = message.get("type")

    if msg_type == "audio_data":
        await handle_audio_data(message)
    elif msg_type == "audio_end":
        await handle_audio_end()
    elif msg_type == "interrupt":
        # 阶段 5 实现
        pass
    else:
        await manager.send_error(ErrorCode.UNKNOWN_ERROR, f"Unknown message type: {msg_type}")


async def handle_audio_data(message: dict[str, object]) -> None:
    """处理音频数据消息."""
    data = message.get("data", {})
    if not isinstance(data, dict):
        await manager.send_error(ErrorCode.ASR_ERROR, "Invalid audio data format")
        return

    audio = data.get("audio", "")
    seq = data.get("seq", 0)

    if not audio:
        return

    # 确保 ASR 服务已启动
    if not manager.asr_service or not manager.asr_service.is_connected:
        connected = await manager.start_asr()
        if not connected:
            return

    # 转发音频数据到 ASR 服务
    if manager.asr_service:
        await manager.asr_service.send_audio(audio, seq, is_last=False)


async def handle_audio_end() -> None:
    """处理音频结束消息."""
    if manager.asr_service and manager.asr_service.is_connected:
        # 发送最后一帧空数据
        await manager.asr_service.send_audio("", manager.asr_service._seq + 1, is_last=True)
        # 发送 ASR 结束消息
        await manager.send_asr_end()
        # 停止 ASR 服务
        await manager.stop_asr()


async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket 端点处理函数."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_message(message, websocket)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                await manager.send_error(ErrorCode.UNKNOWN_ERROR, f"Invalid JSON: {e}")
    except WebSocketDisconnect:
        await manager.disconnect()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await manager.send_error(ErrorCode.UNKNOWN_ERROR, str(e))
        except Exception:
            pass  # 可能连接已断开
        await manager.disconnect()
