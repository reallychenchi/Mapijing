# 实现计划 - 阶段 3：语音识别（ASR）

> 版本：1.0
> 更新日期：2026-02-07

## 阶段目标

实现前端录音功能和后端语音识别代理，完成用户语音到文字的转换流程，实时展示识别结果。

**前置条件：** 阶段 2 完成（WebSocket 通信机制）

---

## 1. 任务清单

| 序号 | 任务 | 类型 | 可单元测试 |
|------|------|------|-----------|
| 3.1 | 前端麦克风权限获取 | 前端 | 部分 |
| 3.2 | 前端音频录制与处理 | 前端 | ✓ |
| 3.3 | 后端火山引擎 ASR 代理 | 后端 | ✓ |
| 3.4 | ASR 消息流转集成 | 前后端 | ✓ |
| 3.5 | 识别结果流式展示 | 前端 | ✓ |
| 3.6 | 录音状态管理 | 前端 | ✓ |

---

## 2. 详细任务说明

### 2.1 前端麦克风权限获取

**文件：** `frontend/src/hooks/useMediaPermission.ts`

**功能：**
- 检查麦克风权限状态
- 请求麦克风权限
- 处理权限拒绝场景

**实现：**
```typescript
import { useState, useCallback } from 'react';

export type PermissionState = 'prompt' | 'granted' | 'denied' | 'checking';

interface UseMediaPermissionReturn {
  state: PermissionState;
  request: () => Promise<boolean>;
  error: string | null;
}

export function useMediaPermission(): UseMediaPermissionReturn {
  const [state, setState] = useState<PermissionState>('prompt');
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(async (): Promise<boolean> => {
    setState('checking');
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // 立即释放，仅用于权限检查
      stream.getTracks().forEach(track => track.stop());
      setState('granted');
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : '麦克风权限获取失败';
      setError(message);
      setState('denied');
      return false;
    }
  }, []);

  return { state, request, error };
}
```

---

### 3.2 前端音频录制与处理

**文件：** `frontend/src/services/audioProcessor.ts`

**功能：**
- 降采样：浏览器采样率（44.1kHz/48kHz）→ 16kHz
- 格式转换：Float32 → Int16 PCM
- 生成可发送的音频数据

**实现：**
```typescript
/**
 * 降采样函数
 * @param buffer 原始音频数据 Float32Array
 * @param fromSampleRate 原始采样率
 * @param toSampleRate 目标采样率（16000）
 */
export function downsampleBuffer(
  buffer: Float32Array,
  fromSampleRate: number,
  toSampleRate: number
): Float32Array {
  if (fromSampleRate === toSampleRate) {
    return buffer;
  }

  const ratio = fromSampleRate / toSampleRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const index = Math.round(i * ratio);
    result[i] = buffer[index];
  }

  return result;
}

/**
 * Float32 转 Int16 PCM
 * @param float32Array Float32 音频数据
 */
export function float32ToInt16(float32Array: Float32Array): Int16Array {
  const int16Array = new Int16Array(float32Array.length);

  for (let i = 0; i < float32Array.length; i++) {
    // 限制范围 [-1, 1]
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    // 转换为 Int16
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  return int16Array;
}

/**
 * Int16Array 转 Base64
 */
export function int16ToBase64(int16Array: Int16Array): string {
  const uint8Array = new Uint8Array(int16Array.buffer);
  let binary = '';
  for (let i = 0; i < uint8Array.length; i++) {
    binary += String.fromCharCode(uint8Array[i]);
  }
  return btoa(binary);
}

/**
 * 处理音频数据：降采样 + 格式转换 + Base64 编码
 */
export function processAudioData(
  buffer: Float32Array,
  fromSampleRate: number
): string {
  const downsampled = downsampleBuffer(buffer, fromSampleRate, 16000);
  const int16Data = float32ToInt16(downsampled);
  return int16ToBase64(int16Data);
}
```

**文件：** `frontend/src/hooks/useAudioRecorder.ts`

**功能：**
- 管理录音状态
- 使用 Web Audio API 采集音频
- 实时发送音频数据

**实现：**
```typescript
import { useState, useCallback, useRef } from 'react';
import { processAudioData } from '../services/audioProcessor';

export type RecordingState = 'idle' | 'recording' | 'stopping';

interface UseAudioRecorderOptions {
  onAudioData: (base64Audio: string, seq: number) => void;
  onError: (error: string) => void;
}

interface UseAudioRecorderReturn {
  state: RecordingState;
  start: () => Promise<void>;
  stop: () => void;
}

export function useAudioRecorder(options: UseAudioRecorderOptions): UseAudioRecorderReturn {
  const { onAudioData, onError } = options;

  const [state, setState] = useState<RecordingState>('idle');
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const seqRef = useRef<number>(0);

  const start = useCallback(async () => {
    try {
      setState('recording');
      seqRef.current = 0;

      // 获取麦克风流
      mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,  // 请求 16kHz，浏览器可能不支持
          echoCancellation: true,
          noiseSuppression: true,
        }
      });

      // 创建 AudioContext
      audioContextRef.current = new AudioContext();
      const source = audioContextRef.current.createMediaStreamSource(mediaStreamRef.current);
      const sampleRate = audioContextRef.current.sampleRate;

      // 创建 ScriptProcessorNode（4096 样本 ≈ 85ms @ 48kHz）
      processorRef.current = audioContextRef.current.createScriptProcessor(4096, 1, 1);

      processorRef.current.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        const base64Audio = processAudioData(inputData, sampleRate);
        seqRef.current += 1;
        onAudioData(base64Audio, seqRef.current);
      };

      // 连接节点
      source.connect(processorRef.current);
      processorRef.current.connect(audioContextRef.current.destination);

    } catch (err) {
      const message = err instanceof Error ? err.message : '录音启动失败';
      onError(message);
      setState('idle');
    }
  }, [onAudioData, onError]);

  const stop = useCallback(() => {
    setState('stopping');

    // 断开处理器
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // 关闭 AudioContext
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // 停止媒体流
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    setState('idle');
  }, []);

  return { state, start, stop };
}
```

---

### 3.3 后端火山引擎 ASR 代理

**参考：** `../ScriptBuddy/api/proxy/asr_proxy.py`

**文件：** `backend/services/asr_service.py`

**功能：**
- 连接火山引擎 ASR WebSocket
- 转发客户端音频数据
- 接收识别结果并返回

**配置：** `backend/config/settings.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 火山引擎 ASR 配置
    VOLC_ASR_URL: str = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
    VOLC_ASR_APP_ID: str = ""
    VOLC_ASR_ACCESS_KEY: str = ""

    # DeepSeek LLM 配置（阶段 4 使用）
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/chat/completions"
    DEEPSEEK_API_KEY: str = ""

    # 火山引擎 TTS 配置（阶段 5 使用）
    VOLC_TTS_URL: str = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
    VOLC_TTS_APP_ID: str = ""
    VOLC_TTS_ACCESS_KEY: str = ""
    VOLC_TTS_CLUSTER: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

**实现：** `backend/services/asr_service.py`

```python
import asyncio
import json
import logging
import websockets
from typing import AsyncGenerator, Callable
from config.settings import settings
from utils.protocol import (
    build_full_client_request,
    build_audio_only_request,
    parse_response
)

logger = logging.getLogger(__name__)

class ASRService:
    """火山引擎 ASR 服务代理"""

    def __init__(self):
        self.ws = None
        self.is_running = False

    async def start_session(self) -> bool:
        """建立 ASR 连接"""
        try:
            extra_headers = {
                "X-Api-App-Key": settings.VOLC_ASR_APP_ID,
                "X-Api-Access-Key": settings.VOLC_ASR_ACCESS_KEY,
            }

            self.ws = await websockets.connect(
                settings.VOLC_ASR_URL,
                additional_headers=extra_headers
            )

            # 发送初始配置
            config = {
                "audio": {
                    "format": "pcm",
                    "codec": "raw",
                    "rate": 16000,
                    "bits": 16,
                    "channel": 1
                },
                "request": {
                    "model_name": "bigmodel",
                    "enable_itn": True,
                    "result_type": "full"
                }
            }

            await self.ws.send(build_full_client_request(config))
            self.is_running = True
            logger.info("ASR session started")
            return True

        except Exception as e:
            logger.error(f"Failed to start ASR session: {e}")
            return False

    async def send_audio(self, audio_data: bytes, seq: int, is_last: bool = False):
        """发送音频数据"""
        if not self.ws or not self.is_running:
            raise RuntimeError("ASR session not started")

        frame = build_audio_only_request(audio_data, seq, is_last)
        await self.ws.send(frame)

    async def receive_results(self) -> AsyncGenerator[dict, None]:
        """接收识别结果"""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                result = parse_response(message)
                if result:
                    yield result

                # 检查是否结束
                if result and result.get("is_final"):
                    break

        except websockets.exceptions.ConnectionClosed:
            logger.info("ASR connection closed")
        except Exception as e:
            logger.error(f"ASR receive error: {e}")
            raise

    async def stop_session(self):
        """关闭 ASR 连接"""
        self.is_running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
        logger.info("ASR session stopped")
```

**协议工具：** `backend/utils/protocol.py`

```python
import json
import struct
import gzip
from typing import Optional

# 协议常量
PROTOCOL_VERSION = 0b0001
HEADER_SIZE = 0b0001
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_REQUEST = 0b0010
FULL_SERVER_RESPONSE = 0b1001
JSON_SERIALIZATION = 0b0001
NO_COMPRESSION = 0b0000
GZIP_COMPRESSION = 0b0001

def build_header(message_type: int, flags: int = 0, serialization: int = JSON_SERIALIZATION,
                 compression: int = NO_COMPRESSION) -> bytes:
    """构建 4 字节协议头"""
    byte0 = (PROTOCOL_VERSION << 4) | HEADER_SIZE
    byte1 = (message_type << 4) | flags
    byte2 = (serialization << 4) | compression
    byte3 = 0x00
    return bytes([byte0, byte1, byte2, byte3])

def build_full_client_request(payload: dict, seq: int = 0) -> bytes:
    """构建完整客户端请求（初始配置）"""
    header = build_header(FULL_CLIENT_REQUEST)
    payload_bytes = json.dumps(payload).encode('utf-8')

    # 4 字节序列号 + payload
    seq_bytes = struct.pack('>I', seq)
    return header + seq_bytes + payload_bytes

def build_audio_only_request(audio_data: bytes, seq: int, is_last: bool = False) -> bytes:
    """构建仅音频请求"""
    flags = 0b0010 if is_last else 0b0000  # NEG flag for last frame
    header = build_header(AUDIO_ONLY_REQUEST, flags=flags, serialization=0b0000)

    # 4 字节序列号 + 音频数据
    seq_bytes = struct.pack('>I', seq)
    return header + seq_bytes + audio_data

def parse_response(data: bytes) -> Optional[dict]:
    """解析服务端响应"""
    if len(data) < 4:
        return None

    # 解析头部
    byte1 = data[1]
    byte2 = data[2]

    message_type = (byte1 >> 4) & 0x0f
    compression = byte2 & 0x0f

    if message_type != FULL_SERVER_RESPONSE:
        return None

    # 跳过头部（4字节）和序列号（4字节）
    payload_start = 8
    payload = data[payload_start:]

    # 解压缩
    if compression == GZIP_COMPRESSION:
        payload = gzip.decompress(payload)

    # 解析 JSON
    try:
        result = json.loads(payload.decode('utf-8'))
        return extract_asr_result(result)
    except Exception:
        return None

def extract_asr_result(response: dict) -> Optional[dict]:
    """从火山引擎响应中提取 ASR 结果"""
    payload = response.get("payload", {})
    result_list = payload.get("result", [])

    if not result_list:
        return None

    result = result_list[0]
    text = result.get("text", "")
    is_final = result.get("type", "") == "final"

    return {
        "text": text,
        "is_final": is_final
    }
```

---

### 3.4 ASR 消息流转集成

**更新：** `backend/api/websocket.py`

```python
import base64
from services.asr_service import ASRService

# 在 ConnectionManager 中添加 ASR 服务
class ConnectionManager:
    def __init__(self):
        self.active_connection: WebSocket | None = None
        self.asr_service: ASRService | None = None
        self.asr_task: asyncio.Task | None = None

    async def start_asr(self):
        """启动 ASR 会话"""
        self.asr_service = ASRService()
        success = await self.asr_service.start_session()
        if success:
            # 启动结果接收任务
            self.asr_task = asyncio.create_task(self._receive_asr_results())
        return success

    async def _receive_asr_results(self):
        """接收并转发 ASR 结果"""
        if not self.asr_service:
            return

        try:
            async for result in self.asr_service.receive_results():
                if result["is_final"]:
                    await self.send_message({
                        "type": "asr_end",
                        "data": {"text": result["text"]}
                    })
                else:
                    await self.send_message({
                        "type": "asr_result",
                        "data": {
                            "text": result["text"],
                            "is_final": False
                        }
                    })
        except Exception as e:
            logger.error(f"ASR result receiving error: {e}")
            await self.send_error("ASR_ERROR", str(e))

    async def stop_asr(self):
        """停止 ASR 会话"""
        if self.asr_task:
            self.asr_task.cancel()
            self.asr_task = None

        if self.asr_service:
            await self.asr_service.stop_session()
            self.asr_service = None

# 更新消息处理
async def handle_message(message: dict, websocket: WebSocket):
    msg_type = message.get("type")

    if msg_type == "audio_data":
        data = message.get("data", {})
        audio_base64 = data.get("audio", "")
        seq = data.get("seq", 0)

        # Base64 解码
        audio_bytes = base64.b64decode(audio_base64)

        # 如果 ASR 未启动，先启动
        if not manager.asr_service:
            await manager.start_asr()

        # 发送音频数据
        if manager.asr_service:
            await manager.asr_service.send_audio(audio_bytes, seq)

    elif msg_type == "audio_end":
        # 发送最后一帧标记
        if manager.asr_service:
            await manager.asr_service.send_audio(b"", 0, is_last=True)

    elif msg_type == "interrupt":
        # 停止 ASR
        await manager.stop_asr()
        await manager.send_message({"type": "tts_end", "data": {}})

    else:
        await manager.send_error("UNKNOWN_ERROR", f"Unknown message type: {msg_type}")
```

---

### 3.5 识别结果流式展示

**更新：** `frontend/src/components/TextArea/TextArea.tsx`

```typescript
import React, { useEffect, useRef } from 'react';
import { ErrorDisplay } from './ErrorDisplay';
import './TextArea.css';

export type Speaker = 'user' | 'assistant';

interface TextAreaProps {
  text: string;
  speaker: Speaker;
  isStreaming: boolean;
  error?: {
    code: string;
    message: string;
    onRetry: () => void;
  };
}

export const TextArea: React.FC<TextAreaProps> = ({
  text,
  speaker,
  isStreaming,
  error
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [text]);

  if (error) {
    return (
      <div className="text-area">
        <ErrorDisplay
          code={error.code as any}
          message={error.message}
          onRetry={error.onRetry}
        />
      </div>
    );
  }

  return (
    <div className="text-area" ref={containerRef}>
      <div className={`text-content ${speaker}`}>
        {text}
        {isStreaming && <span className="cursor">|</span>}
      </div>
    </div>
  );
};
```

**样式更新：** `frontend/src/components/TextArea/TextArea.css`

```css
.text-area {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow-y: auto;
}

.text-content {
  font-size: 18px;
  line-height: 1.6;
  text-align: center;
  max-width: 80%;
}

.text-content.user {
  color: #333;
}

.text-content.assistant {
  color: #007bff;
}

.cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}
```

---

### 3.6 录音状态管理

**文件：** `frontend/src/hooks/useConversation.ts`

**功能：**
- 管理整体对话状态
- 协调录音、识别、展示

```typescript
import { useState, useCallback, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAudioRecorder } from './useAudioRecorder';
import { ServerMessage, AsrResultMessage, AsrEndMessage } from '../types/message';
import { EmotionType } from '../types/emotion';

export type ConversationState =
  | 'idle'           // 空闲，等待用户说话
  | 'listening'      // 用户正在说话
  | 'processing'     // 处理中（ASR/LLM/TTS）
  | 'speaking'       // AI 正在说话
  | 'error';         // 出错

interface UseConversationReturn {
  state: ConversationState;
  text: string;
  speaker: 'user' | 'assistant';
  emotion: EmotionType;
  error: { code: string; message: string } | null;
  startListening: () => void;
  stopListening: () => void;
  retry: () => void;
}

export function useConversation(): UseConversationReturn {
  const [state, setState] = useState<ConversationState>('idle');
  const [text, setText] = useState<string>('');
  const [speaker, setSpeaker] = useState<'user' | 'assistant'>('user');
  const [emotion, setEmotion] = useState<EmotionType>('default');
  const [error, setError] = useState<{ code: string; message: string } | null>(null);

  // 处理服务端消息
  const handleMessage = useCallback((message: ServerMessage) => {
    switch (message.type) {
      case 'asr_result':
        const asrResult = message as AsrResultMessage;
        setText(asrResult.data.text);
        setSpeaker('user');
        break;

      case 'asr_end':
        const asrEnd = message as AsrEndMessage;
        setText(asrEnd.data.text);
        setState('processing');
        break;

      // 阶段 4、5 实现
      case 'tts_chunk':
      case 'tts_end':
      case 'emotion':
        break;

      case 'error':
        setError({
          code: message.data.code,
          message: message.data.message
        });
        setState('error');
        break;
    }
  }, []);

  // WebSocket 连接
  const { state: wsState, send, connect } = useWebSocket({
    onMessage: handleMessage,
    onError: (err) => {
      setError({ code: err.data.code, message: err.data.message });
      setState('error');
    }
  });

  // 录音
  const { state: recState, start: startRecording, stop: stopRecording } = useAudioRecorder({
    onAudioData: (audio, seq) => {
      send({ type: 'audio_data', data: { audio, seq } });
    },
    onError: (msg) => {
      setError({ code: 'ASR_ERROR', message: msg });
      setState('error');
    }
  });

  // 开始监听
  const startListening = useCallback(() => {
    setError(null);
    setText('');
    setSpeaker('user');
    setState('listening');
    startRecording();
  }, [startRecording]);

  // 停止监听
  const stopListening = useCallback(() => {
    stopRecording();
    send({ type: 'audio_end', data: {} });
  }, [stopRecording, send]);

  // 重试
  const retry = useCallback(() => {
    setError(null);
    setState('idle');
    connect();
  }, [connect]);

  return {
    state,
    text,
    speaker,
    emotion,
    error,
    startListening,
    stopListening,
    retry,
  };
}
```

---

## 3. 测试计划

### 3.1 单元测试

| 测试对象 | 测试内容 | 文件 |
|----------|----------|------|
| audioProcessor | 降采样、格式转换、Base64 编码 | `audioProcessor.test.ts` |
| useAudioRecorder | 录音状态管理（Mock） | `useAudioRecorder.test.ts` |
| useConversation | 对话状态流转 | `useConversation.test.ts` |
| ASRService | ASR 连接、消息发送（Mock） | `test_asr_service.py` |
| protocol | 协议编解码 | `test_protocol.py` |

**前端测试示例（audioProcessor）：**

```typescript
// frontend/src/services/audioProcessor.test.ts
import { describe, it, expect } from 'vitest';
import { downsampleBuffer, float32ToInt16, int16ToBase64 } from './audioProcessor';

describe('audioProcessor', () => {
  describe('downsampleBuffer', () => {
    it('should return same buffer when sample rates match', () => {
      const input = new Float32Array([0.1, 0.2, 0.3, 0.4]);
      const result = downsampleBuffer(input, 16000, 16000);
      expect(result).toEqual(input);
    });

    it('should downsample 48kHz to 16kHz', () => {
      const input = new Float32Array(48);
      input.fill(0.5);
      const result = downsampleBuffer(input, 48000, 16000);
      expect(result.length).toBe(16);
    });
  });

  describe('float32ToInt16', () => {
    it('should convert 0 correctly', () => {
      const input = new Float32Array([0]);
      const result = float32ToInt16(input);
      expect(result[0]).toBe(0);
    });

    it('should convert 1 to max positive', () => {
      const input = new Float32Array([1]);
      const result = float32ToInt16(input);
      expect(result[0]).toBe(32767);
    });

    it('should convert -1 to max negative', () => {
      const input = new Float32Array([-1]);
      const result = float32ToInt16(input);
      expect(result[0]).toBe(-32768);
    });
  });

  describe('int16ToBase64', () => {
    it('should encode correctly', () => {
      const input = new Int16Array([0, 1, 255]);
      const result = int16ToBase64(input);
      expect(typeof result).toBe('string');
      expect(result.length).toBeGreaterThan(0);
    });
  });
});
```

**后端测试示例（protocol）：**

```python
# backend/tests/test_protocol.py
import pytest
from utils.protocol import (
    build_header,
    build_full_client_request,
    build_audio_only_request,
    parse_response
)

def test_build_header():
    header = build_header(0b0001)
    assert len(header) == 4
    assert header[0] == 0x11  # version=1, header_size=1

def test_build_full_client_request():
    payload = {"test": "data"}
    result = build_full_client_request(payload, seq=1)
    assert len(result) > 8  # header(4) + seq(4) + payload

def test_build_audio_only_request():
    audio = b'\x00\x01\x02\x03'
    result = build_audio_only_request(audio, seq=1)
    assert len(result) == 4 + 4 + len(audio)

def test_build_audio_only_request_last_frame():
    audio = b''
    result = build_audio_only_request(audio, seq=99, is_last=True)
    # flags should have NEG bit set
    assert (result[1] & 0x0f) == 0b0010
```

### 3.2 手工测试

| 测试项 | 验证内容 | 测试方法 |
|--------|----------|----------|
| 麦克风权限 | 首次访问弹出权限请求 | 清除权限后访问页面 |
| 录音启动 | 点击/触发后开始录音 | 检查浏览器麦克风图标 |
| 流式识别 | 说话时实时显示文字 | 持续说话观察文字更新 |
| 识别完成 | 停止说话后显示完整文字 | 说完一句话检查最终结果 |
| ASR 错误 | 服务异常时显示错误 | 停止后端 ASR 代理 |

---

## 4. 交付物

完成本阶段后，应具备：

- [ ] 麦克风权限请求正常
- [ ] 录音功能正常（可采集音频）
- [ ] 音频处理正确（降采样、格式转换）
- [ ] 后端 ASR 代理连接火山引擎正常
- [ ] ASR 识别结果实时返回前端
- [ ] 文字区域流式展示识别结果
- [ ] ASR 错误正确处理和展示
- [ ] 单元测试全部通过

---

## 5. 环境配置

本阶段需要配置火山引擎 ASR 凭证：

**文件：** `backend/.env`

```bash
# 火山引擎 ASR 配置
VOLC_ASR_APP_ID=your_app_id
VOLC_ASR_ACCESS_KEY=your_access_key
```

**获取方式：** 参考 `../ScriptBuddy/doc/TTS_ASR_Configuration_Guide.md`

---

## 6. 预计产出文件

```
Mapijing/
├── frontend/src/
│   ├── services/
│   │   ├── audioProcessor.ts       # 音频处理
│   │   └── audioProcessor.test.ts
│   │
│   ├── hooks/
│   │   ├── useMediaPermission.ts   # 麦克风权限
│   │   ├── useAudioRecorder.ts     # 录音管理
│   │   ├── useAudioRecorder.test.ts
│   │   ├── useConversation.ts      # 对话状态管理
│   │   └── useConversation.test.ts
│   │
│   └── components/
│       └── TextArea/
│           ├── TextArea.tsx        # 更新：流式展示
│           └── TextArea.css
│
└── backend/
    ├── config/
    │   └── settings.py             # 配置项
    │
    ├── services/
    │   ├── asr_service.py          # ASR 服务
    │   └── __init__.py
    │
    ├── utils/
    │   ├── protocol.py             # 协议封装
    │   └── __init__.py
    │
    ├── api/
    │   └── websocket.py            # 更新：ASR 集成
    │
    ├── tests/
    │   ├── test_asr_service.py
    │   └── test_protocol.py
    │
    └── .env                        # 环境配置
```
