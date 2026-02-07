"""WebSocket 端点测试."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端."""
    return TestClient(app)


def test_websocket_connect(client: TestClient) -> None:
    """测试 WebSocket 连接."""
    with client.websocket_connect("/ws/chat") as websocket:
        # 连接成功不会抛出异常
        assert websocket is not None


def test_websocket_receive_error_on_unknown_type(client: TestClient) -> None:
    """测试发送未知消息类型时返回错误."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "unknown_type", "data": {}})
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert response["data"]["code"] == "UNKNOWN_ERROR"
        assert "Unknown message type" in response["data"]["message"]


def test_websocket_disconnect(client: TestClient) -> None:
    """测试 WebSocket 正常断开."""
    with client.websocket_connect("/ws/chat") as _websocket:
        pass  # 正常断开不应抛出异常


def test_websocket_invalid_json(client: TestClient) -> None:
    """测试发送无效 JSON."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_text("invalid json {{{")
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert response["data"]["code"] == "UNKNOWN_ERROR"
        assert "Invalid JSON" in response["data"]["message"]


def test_websocket_audio_data_message(client: TestClient) -> None:
    """测试发送 audio_data 消息（阶段 3 实现，目前不返回响应）."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "audio_data", "data": {"audio": "base64", "seq": 1}})
        # 阶段 3 实现后会有响应，目前该消息被静默处理


def test_websocket_audio_end_message(client: TestClient) -> None:
    """测试发送 audio_end 消息（阶段 3 实现，目前不返回响应）."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "audio_end", "data": {}})
        # 阶段 3 实现后会有响应，目前该消息被静默处理


def test_websocket_interrupt_message(client: TestClient) -> None:
    """测试发送 interrupt 消息（阶段 5 实现，目前不返回响应）."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "interrupt", "data": {}})
        # 阶段 5 实现后会有响应，目前该消息被静默处理


def test_websocket_error_response_has_timestamp(client: TestClient) -> None:
    """测试错误响应包含时间戳."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "unknown", "data": {}})
        response = websocket.receive_json()
        assert "timestamp" in response
        assert isinstance(response["timestamp"], int)
