# 实现计划 - 阶段 2：WebSocket 通信

> 版本：1.0
> 更新日期：2026-02-07

## 阶段目标

建立前后端 WebSocket 通信机制，实现消息收发、连接管理和错误处理，为后续语音和对话功能提供通信基础。

**前置条件：** 阶段 1 完成（前后端项目骨架、基础 UI 组件）

---

## 1. 任务清单

| 序号 | 任务 | 类型 | 可单元测试 |
|------|------|------|-----------|
| 2.1 | 后端 WebSocket 端点 | 后端 | ✓ |
| 2.2 | 消息类型定义 | 前后端 | ✓ |
| 2.3 | 前端 WebSocket 服务 | 前端 | ✓ |
| 2.4 | 前端连接状态管理 | 前端 | ✓ |
| 2.5 | 错误处理与重试机制 | 前后端 | ✓ |
| 2.6 | 连接状态 UI 反馈 | 前端 | ✓ |

---

## 2. 详细任务说明

### 2.1 后端 WebSocket 端点

**文件：** `backend/api/websocket.py`

**功能：**
- 创建 WebSocket 端点 `/ws/chat`
- 管理连接生命周期
- 接收和发送 JSON 消息
- 处理连接异常

**实现：**
```python
# backend/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connection: WebSocket | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connection = websocket
        logger.info("WebSocket connected")

    def disconnect(self):
        self.active_connection = None
        logger.info("WebSocket disconnected")

    async def send_message(self, message: dict):
        if self.active_connection:
            await self.active_connection.send_json(message)

    async def send_error(self, code: str, message: str):
        await self.send_message({
            "type": "error",
            "data": {
                "code": code,
                "message": message
            }
        })

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(message, websocket)
    except WebSocketDisconnect:
        manager.disconnect()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.send_error("UNKNOWN_ERROR", str(e))
        manager.disconnect()

async def handle_message(message: dict, websocket: WebSocket):
    """消息路由处理"""
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
        await manager.send_error("UNKNOWN_ERROR", f"Unknown message type: {msg_type}")
```

**注册路由：**
```python
# backend/main.py
from fastapi import FastAPI, WebSocket
from api.websocket import websocket_endpoint

app = FastAPI(title="Mapijing API", version="1.0.0")

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket_endpoint(websocket)
```

---

### 2.2 消息类型定义

**前端文件：** `frontend/src/types/message.ts`

```typescript
// 消息方向
export type MessageDirection = 'client_to_server' | 'server_to_client';

// 客户端发送的消息类型
export type ClientMessageType = 'audio_data' | 'audio_end' | 'interrupt';

// 服务端发送的消息类型
export type ServerMessageType =
  | 'asr_result'
  | 'asr_end'
  | 'tts_chunk'
  | 'tts_end'
  | 'emotion'
  | 'error';

// 错误码
export type ErrorCode =
  | 'ASR_ERROR'
  | 'LLM_ERROR'
  | 'TTS_ERROR'
  | 'NETWORK_ERROR'
  | 'UNKNOWN_ERROR';

// 情感类型（服务端返回的中文值）
export type ServerEmotion = '默认陪伴' | '共情倾听' | '安慰支持' | '轻松愉悦';

// 基础消息结构
export interface BaseMessage<T extends string, D = unknown> {
  type: T;
  data: D;
  timestamp?: number;
}

// === 客户端消息 ===

export interface AudioDataMessage extends BaseMessage<'audio_data', {
  audio: string;  // base64 encoded PCM
  seq: number;
}> {}

export interface AudioEndMessage extends BaseMessage<'audio_end', {}> {}

export interface InterruptMessage extends BaseMessage<'interrupt', {}> {}

export type ClientMessage = AudioDataMessage | AudioEndMessage | InterruptMessage;

// === 服务端消息 ===

export interface AsrResultMessage extends BaseMessage<'asr_result', {
  text: string;
  is_final: boolean;
}> {}

export interface AsrEndMessage extends BaseMessage<'asr_end', {
  text: string;
}> {}

export interface TtsChunkMessage extends BaseMessage<'tts_chunk', {
  text: string;
  audio: string;  // base64 encoded MP3
  seq: number;
  is_final: boolean;
}> {}

export interface TtsEndMessage extends BaseMessage<'tts_end', {
  full_text: string;
}> {}

export interface EmotionMessage extends BaseMessage<'emotion', {
  emotion: ServerEmotion;
}> {}

export interface ErrorMessage extends BaseMessage<'error', {
  code: ErrorCode;
  message: string;
}> {}

export type ServerMessage =
  | AsrResultMessage
  | AsrEndMessage
  | TtsChunkMessage
  | TtsEndMessage
  | EmotionMessage
  | ErrorMessage;
```

**后端文件：** `backend/models/message.py`

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Union

class ClientMessageType(str, Enum):
    AUDIO_DATA = "audio_data"
    AUDIO_END = "audio_end"
    INTERRUPT = "interrupt"

class ServerMessageType(str, Enum):
    ASR_RESULT = "asr_result"
    ASR_END = "asr_end"
    TTS_CHUNK = "tts_chunk"
    TTS_END = "tts_end"
    EMOTION = "emotion"
    ERROR = "error"

class ErrorCode(str, Enum):
    ASR_ERROR = "ASR_ERROR"
    LLM_ERROR = "LLM_ERROR"
    TTS_ERROR = "TTS_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class EmotionType(str, Enum):
    DEFAULT = "默认陪伴"
    EMPATHY = "共情倾听"
    COMFORT = "安慰支持"
    HAPPY = "轻松愉悦"

# 服务端发送的消息
class AsrResultData(BaseModel):
    text: str
    is_final: bool

class AsrEndData(BaseModel):
    text: str

class TtsChunkData(BaseModel):
    text: str
    audio: str  # base64
    seq: int
    is_final: bool

class TtsEndData(BaseModel):
    full_text: str

class EmotionData(BaseModel):
    emotion: EmotionType

class ErrorData(BaseModel):
    code: ErrorCode
    message: str

class ServerMessage(BaseModel):
    type: ServerMessageType
    data: Union[AsrResultData, AsrEndData, TtsChunkData, TtsEndData, EmotionData, ErrorData]
    timestamp: Optional[int] = None
```

---

### 2.3 前端 WebSocket 服务

**文件：** `frontend/src/services/websocket.ts`

**功能：**
- 建立和管理 WebSocket 连接
- 发送和接收消息
- 连接状态监控
- 自动序列化/反序列化

**实现：**
```typescript
import { ClientMessage, ServerMessage } from '../types/message';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export type MessageHandler = (message: ServerMessage) => void;
export type StateChangeHandler = (state: ConnectionState) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private messageHandlers: Set<MessageHandler> = new Set();
  private stateChangeHandlers: Set<StateChangeHandler> = new Set();
  private _state: ConnectionState = 'disconnected';

  constructor(url: string) {
    this.url = url;
  }

  get state(): ConnectionState {
    return this._state;
  }

  private setState(state: ConnectionState) {
    this._state = state;
    this.stateChangeHandlers.forEach(handler => handler(state));
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      this.setState('connecting');
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.setState('connected');
        resolve();
      };

      this.ws.onclose = () => {
        this.setState('disconnected');
      };

      this.ws.onerror = (error) => {
        this.setState('error');
        reject(error);
      };

      this.ws.onmessage = (event) => {
        try {
          const message: ServerMessage = JSON.parse(event.data);
          this.messageHandlers.forEach(handler => handler(message));
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };
    });
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setState('disconnected');
  }

  send(message: ClientMessage) {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }
    this.ws.send(JSON.stringify(message));
  }

  onMessage(handler: MessageHandler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStateChange(handler: StateChangeHandler) {
    this.stateChangeHandlers.add(handler);
    return () => this.stateChangeHandlers.delete(handler);
  }
}

// 单例导出
let wsService: WebSocketService | null = null;

export function getWebSocketService(): WebSocketService {
  if (!wsService) {
    const wsUrl = `ws://${window.location.hostname}:8000/ws/chat`;
    wsService = new WebSocketService(wsUrl);
  }
  return wsService;
}
```

---

### 2.4 前端连接状态管理

**文件：** `frontend/src/hooks/useWebSocket.ts`

**功能：**
- 封装 WebSocket 服务为 React Hook
- 管理连接生命周期
- 提供消息发送和接收接口

**实现：**
```typescript
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getWebSocketService,
  WebSocketService,
  ConnectionState
} from '../services/websocket';
import { ClientMessage, ServerMessage, ErrorMessage } from '../types/message';

interface UseWebSocketOptions {
  autoConnect?: boolean;
  onMessage?: (message: ServerMessage) => void;
  onError?: (error: ErrorMessage) => void;
}

interface UseWebSocketReturn {
  state: ConnectionState;
  connect: () => Promise<void>;
  disconnect: () => void;
  send: (message: ClientMessage) => void;
  error: ErrorMessage | null;
  clearError: () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { autoConnect = true, onMessage, onError } = options;

  const [state, setState] = useState<ConnectionState>('disconnected');
  const [error, setError] = useState<ErrorMessage | null>(null);
  const wsRef = useRef<WebSocketService | null>(null);

  useEffect(() => {
    wsRef.current = getWebSocketService();

    // 订阅状态变化
    const unsubState = wsRef.current.onStateChange(setState);

    // 订阅消息
    const unsubMessage = wsRef.current.onMessage((message) => {
      if (message.type === 'error') {
        setError(message as ErrorMessage);
        onError?.(message as ErrorMessage);
      } else {
        onMessage?.(message);
      }
    });

    // 自动连接
    if (autoConnect) {
      wsRef.current.connect().catch(console.error);
    }

    return () => {
      unsubState();
      unsubMessage();
    };
  }, [autoConnect, onMessage, onError]);

  const connect = useCallback(async () => {
    setError(null);
    await wsRef.current?.connect();
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
  }, []);

  const send = useCallback((message: ClientMessage) => {
    wsRef.current?.send(message);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    state,
    connect,
    disconnect,
    send,
    error,
    clearError,
  };
}
```

---

### 2.5 错误处理与重试机制

**前端错误处理组件更新：**

**文件：** `frontend/src/components/TextArea/ErrorDisplay.tsx`

```typescript
import React from 'react';
import { ErrorCode } from '../../types/message';
import './ErrorDisplay.css';

interface ErrorDisplayProps {
  code: ErrorCode;
  message: string;
  onRetry: () => void;
}

const ERROR_LABELS: Record<ErrorCode, string> = {
  ASR_ERROR: '语音识别错误',
  LLM_ERROR: '对话服务错误',
  TTS_ERROR: '语音合成错误',
  NETWORK_ERROR: '网络连接错误',
  UNKNOWN_ERROR: '未知错误',
};

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  code,
  message,
  onRetry
}) => {
  return (
    <div className="error-display">
      <div className="error-icon">⚠️</div>
      <div className="error-title">{ERROR_LABELS[code]}</div>
      <div className="error-message">{message}</div>
      <button className="retry-button" onClick={onRetry}>
        点击重试
      </button>
    </div>
  );
};
```

**样式文件：** `frontend/src/components/TextArea/ErrorDisplay.css`

```css
.error-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  text-align: center;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-title {
  color: #dc3545;
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 8px;
}

.error-message {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
}

.retry-button {
  background-color: #dc3545;
  color: white;
  border: none;
  padding: 12px 24px;
  font-size: 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.retry-button:hover {
  background-color: #c82333;
}

.retry-button:active {
  background-color: #bd2130;
}
```

---

### 2.6 连接状态 UI 反馈

**文件：** `frontend/src/components/ConnectionStatus/ConnectionStatus.tsx`

**功能：**
- 显示当前连接状态
- 提供手动重连按钮

```typescript
import React from 'react';
import { ConnectionState } from '../../services/websocket';
import './ConnectionStatus.css';

interface ConnectionStatusProps {
  state: ConnectionState;
  onReconnect: () => void;
}

const STATUS_CONFIG: Record<ConnectionState, { label: string; color: string }> = {
  disconnected: { label: '未连接', color: '#999' },
  connecting: { label: '连接中...', color: '#ffc107' },
  connected: { label: '已连接', color: '#28a745' },
  error: { label: '连接错误', color: '#dc3545' },
};

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  state,
  onReconnect
}) => {
  const config = STATUS_CONFIG[state];

  return (
    <div className="connection-status">
      <span
        className="status-indicator"
        style={{ backgroundColor: config.color }}
      />
      <span className="status-label">{config.label}</span>
      {(state === 'disconnected' || state === 'error') && (
        <button className="reconnect-button" onClick={onReconnect}>
          重新连接
        </button>
      )}
    </div>
  );
};
```

**样式文件：** `frontend/src/components/ConnectionStatus/ConnectionStatus.css`

```css
.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 12px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-label {
  color: #666;
}

.reconnect-button {
  background: none;
  border: 1px solid #666;
  color: #666;
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 4px;
  cursor: pointer;
}

.reconnect-button:hover {
  background-color: #f0f0f0;
}
```

---

## 3. 测试计划

### 3.1 单元测试

| 测试对象 | 测试内容 | 文件 |
|----------|----------|------|
| 消息类型 | 类型定义正确性、序列化/反序列化 | `message.test.ts` |
| WebSocketService | 连接、断开、消息发送接收 | `websocket.test.ts` |
| useWebSocket Hook | 状态管理、回调触发 | `useWebSocket.test.ts` |
| ErrorDisplay | 错误信息渲染、重试按钮 | `ErrorDisplay.test.tsx` |
| ConnectionStatus | 状态显示、重连按钮 | `ConnectionStatus.test.tsx` |
| 后端 WebSocket | 连接处理、消息路由 | `test_websocket.py` |

**前端测试示例：**

```typescript
// frontend/src/services/websocket.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WebSocketService } from './websocket';

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1;
  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((error: Event) => void) | null = null;

  constructor(url: string) {
    setTimeout(() => this.onopen?.(), 0);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = 3; // CLOSED
    this.onclose?.();
  });
}

(global as any).WebSocket = MockWebSocket;

describe('WebSocketService', () => {
  let service: WebSocketService;

  beforeEach(() => {
    service = new WebSocketService('ws://localhost:8000/ws/chat');
  });

  it('should connect successfully', async () => {
    await service.connect();
    expect(service.state).toBe('connected');
  });

  it('should handle disconnect', async () => {
    await service.connect();
    service.disconnect();
    expect(service.state).toBe('disconnected');
  });

  it('should notify state changes', async () => {
    const handler = vi.fn();
    service.onStateChange(handler);

    await service.connect();

    expect(handler).toHaveBeenCalledWith('connecting');
    expect(handler).toHaveBeenCalledWith('connected');
  });
});
```

**后端测试示例：**

```python
# backend/tests/test_websocket.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_websocket_connect():
    with client.websocket_connect("/ws/chat") as websocket:
        # 连接成功不会抛出异常
        assert websocket is not None

def test_websocket_receive_error_on_unknown_type():
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "unknown_type", "data": {}})
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert response["data"]["code"] == "UNKNOWN_ERROR"

def test_websocket_disconnect():
    with client.websocket_connect("/ws/chat") as websocket:
        pass  # 正常断开不应抛出异常
```

### 3.2 手工测试

| 测试项 | 验证内容 | 测试方法 |
|--------|----------|----------|
| 连接建立 | 页面加载后自动连接成功 | 打开页面，检查状态显示"已连接" |
| 连接断开 | 后端停止后显示断开状态 | 停止后端服务，检查状态变化 |
| 重新连接 | 点击重连按钮可恢复连接 | 断开后点击重连，检查是否恢复 |
| 错误显示 | 发送无效消息显示错误 | 通过控制台发送无效消息，检查错误显示 |
| 重试功能 | 点击重试按钮触发回调 | 点击重试按钮，检查回调是否执行 |

---

## 4. 交付物

完成本阶段后，应具备：

- [ ] 后端 WebSocket 端点可用（`/ws/chat`）
- [ ] 前后端消息类型定义完整
- [ ] 前端 WebSocket 服务正常工作
- [ ] 连接状态正确显示
- [ ] 错误信息正确展示
- [ ] 重试按钮功能正常
- [ ] 单元测试全部通过

---

## 5. 集成验证

本阶段完成后，执行以下验证：

```bash
# 1. 启动后端
cd backend
uvicorn main:app --reload

# 2. 启动前端
cd frontend
npm run dev

# 3. 打开浏览器访问前端
# 检查连接状态显示"已连接"

# 4. 停止后端
# 检查连接状态变为"未连接"

# 5. 重启后端，点击重连
# 检查连接恢复为"已连接"

# 6. 在浏览器控制台发送测试消息
getWebSocketService().send({ type: 'unknown', data: {} });
# 检查是否显示错误信息
```

---

## 6. 预计产出文件

```
Mapijing/
├── frontend/src/
│   ├── types/
│   │   ├── message.ts              # 消息类型定义
│   │   └── message.test.ts
│   │
│   ├── services/
│   │   ├── websocket.ts            # WebSocket 服务
│   │   └── websocket.test.ts
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts         # WebSocket Hook
│   │   └── useWebSocket.test.ts
│   │
│   └── components/
│       ├── TextArea/
│       │   ├── ErrorDisplay.tsx    # 错误显示组件
│       │   ├── ErrorDisplay.css
│       │   └── ErrorDisplay.test.tsx
│       │
│       └── ConnectionStatus/       # 新增
│           ├── ConnectionStatus.tsx
│           ├── ConnectionStatus.css
│           └── ConnectionStatus.test.tsx
│
└── backend/
    ├── api/
    │   ├── __init__.py
    │   └── websocket.py            # WebSocket 端点
    │
    ├── models/
    │   ├── __init__.py
    │   └── message.py              # 消息模型
    │
    └── tests/
        └── test_websocket.py       # WebSocket 测试
```
