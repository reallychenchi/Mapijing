"""WebSocket 端点实现."""

import json
import logging
import time

from fastapi import WebSocket, WebSocketDisconnect

from models.message import ErrorCode, ServerMessageType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器."""

    def __init__(self) -> None:
        """初始化连接管理器."""
        self.active_connection: WebSocket | None = None

    async def connect(self, websocket: WebSocket) -> None:
        """接受并存储连接."""
        await websocket.accept()
        self.active_connection = websocket
        logger.info("WebSocket connected")

    def disconnect(self) -> None:
        """断开连接."""
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


manager = ConnectionManager()


async def handle_message(message: dict[str, object], websocket: WebSocket) -> None:
    """消息路由处理."""
    msg_type = message.get("type")

    if msg_type == "audio_data":
        # 阶段 3 实现
        pass
    elif msg_type == "audio_end":
        # 阶段 3 实现
        pass
    elif msg_type == "interrupt":
        # 阶段 5 实现
        pass
    else:
        await manager.send_error(ErrorCode.UNKNOWN_ERROR, f"Unknown message type: {msg_type}")


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
        manager.disconnect()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await manager.send_error(ErrorCode.UNKNOWN_ERROR, str(e))
        except Exception:
            pass  # 可能连接已断开
        manager.disconnect()
