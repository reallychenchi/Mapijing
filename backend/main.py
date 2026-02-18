import logging
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from api.websocket import websocket_endpoint
from api.e2e_websocket import e2e_websocket_endpoint
from config.settings import settings

# 配置日志级别
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/config")
async def get_config() -> dict[str, list[str]]:
    """Get application configuration."""
    return {"emotion_types": settings.EMOTION_TYPES}


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    """WebSocket 聊天端点."""
    await websocket_endpoint(websocket)


@app.websocket("/ws/e2e-chat")
async def ws_e2e_chat(websocket: WebSocket) -> None:
    """端到端实时语音 WebSocket 端点."""
    await e2e_websocket_endpoint(websocket)
