# 实现计划 - 阶段 5：语音合成（TTS）+ 同步播放

> 版本：1.0
> 更新日期：2026-02-07

## 阶段目标

集成火山引擎 TTS 服务，实现文字音频同步下发（tts_chunk），前端实现播放队列，确保用户看到的文字和听到的语音一致。

**前置条件：** 阶段 4（LLM 对话）已完成

---

## 1. 任务清单

| 序号 | 任务 | 类型 | 可单元测试 |
|------|------|------|-----------|
| 5.1 | 实现 TTS 服务（火山引擎代理） | 后端 | ✓ |
| 5.2 | 实现 LLM 流式调用 | 后端 | ✓ |
| 5.3 | 实现文本分句器 | 后端 | ✓ |
| 5.4 | 实现 tts_chunk 同步下发 | 后端 | ✓ |
| 5.5 | 前端音频播放队列 | 前端 | ✓ |
| 5.6 | 前端文字音频同步展示 | 前端 | ✓ |

---

## 2. 详细任务说明

### 2.1 实现 TTS 服务

**文件：** `backend/services/tts_service.py`

**功能：**
- 连接火山引擎 TTS WebSocket
- 发送文字，接收 MP3 音频
- 支持单句合成

**参考：** `../ScriptBuddy/doc/TTS_ASR_Configuration_Guide.md`

**接口定义：**
```python
from dataclasses import dataclass
from typing import Optional
import asyncio
import websockets
import json
import uuid
import gzip

@dataclass
class TTSConfig:
    """TTS 配置"""
    app_id: str = ""
    token: str = ""
    cluster: str = "volcano_tts"
    voice_type: str = "zh_female_cancan_mars_bigtts"  # 音色
    encoding: str = "mp3"
    speed_ratio: float = 1.0
    volume_ratio: float = 1.0
    pitch_ratio: float = 1.0

@dataclass
class TTSResult:
    """TTS 结果"""
    audio_data: bytes     # MP3 音频二进制
    duration_ms: int      # 音频时长（毫秒）
    success: bool
    error_message: Optional[str] = None

class TTSService:
    """火山引擎 TTS 服务"""

    WS_URL = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"

    def __init__(self, config: TTSConfig):
        self.config = config

    async def synthesize(self, text: str) -> TTSResult:
        """
        合成单句语音

        Args:
            text: 要合成的文字

        Returns:
            TTSResult 对象
        """
        try:
            audio_chunks = []

            async with websockets.connect(
                self.WS_URL,
                additional_headers={"Authorization": f"Bearer; {self.config.token}"}
            ) as ws:
                # 发送请求
                request = self._build_request(text)
                await ws.send(request)

                # 接收响应
                while True:
                    response = await ws.recv()
                    result = self._parse_response(response)

                    if result.get("audio"):
                        audio_chunks.append(result["audio"])

                    if result.get("is_last"):
                        break

                    if result.get("error"):
                        return TTSResult(
                            audio_data=b"",
                            duration_ms=0,
                            success=False,
                            error_message=result["error"]
                        )

            # 合并音频
            full_audio = b"".join(audio_chunks)

            return TTSResult(
                audio_data=full_audio,
                duration_ms=self._estimate_duration(len(full_audio)),
                success=True
            )

        except Exception as e:
            return TTSResult(
                audio_data=b"",
                duration_ms=0,
                success=False,
                error_message=str(e)
            )

    def _build_request(self, text: str) -> bytes:
        """构建 TTS 请求"""
        request_json = {
            "app": {
                "appid": self.config.app_id,
                "token": "access_token",
                "cluster": self.config.cluster
            },
            "user": {
                "uid": "user_" + str(uuid.uuid4())[:8]
            },
            "audio": {
                "voice_type": self.config.voice_type,
                "encoding": self.config.encoding,
                "speed_ratio": self.config.speed_ratio,
                "volume_ratio": self.config.volume_ratio,
                "pitch_ratio": self.config.pitch_ratio,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "submit"
            }
        }

        payload = json.dumps(request_json).encode('utf-8')

        # 协议头部
        # version(1) + header_size(1) + message_type(1) + flags(1) + serialization(1) + compression(1) + reserved(2)
        header = bytes([
            0x11,  # version=1, header_size=1
            0x10,  # message_type=full client request
            0x01,  # flags: has payload
            0x01,  # serialization: json
            0x01,  # compression: gzip
            0x00, 0x00, 0x00  # reserved
        ])

        # 压缩 payload
        compressed = gzip.compress(payload)

        # payload size (4 bytes, big endian)
        size_bytes = len(compressed).to_bytes(4, 'big')

        return header + size_bytes + compressed

    def _parse_response(self, data: bytes) -> dict:
        """解析 TTS 响应"""
        # 参考 ScriptBuddy 实现解析二进制协议
        # 简化版本，实际需要按协议解析
        result = {}

        if len(data) < 4:
            return {"error": "Invalid response"}

        # 解析协议头
        message_type = (data[1] >> 4) & 0x0F

        if message_type == 0x0B:  # audio only
            # 提取音频数据
            payload_size = int.from_bytes(data[4:8], 'big')
            audio_data = data[8:8+payload_size]
            result["audio"] = audio_data

        elif message_type == 0x0F:  # end of response
            result["is_last"] = True

        elif message_type == 0x0C:  # error
            result["error"] = "TTS error"

        return result

    def _estimate_duration(self, audio_size: int) -> int:
        """估算音频时长（毫秒）"""
        # MP3 128kbps: 16KB/s
        return int(audio_size / 16 * 1000)
```

---

### 2.2 实现 LLM 流式调用

**文件：** `backend/services/llm_service.py`（更新）

**新增功能：**
- 实现 `chat_stream` 方法
- 流式返回文字片段

**更新代码：**
```python
async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
    """
    流式对话

    Args:
        messages: 对话历史

    Yields:
        文字片段
    """
    full_messages = [
        {"role": "system", "content": self.SYSTEM_PROMPT},
        *messages
    ]

    payload = {
        "model": self.config.model,
        "messages": full_messages,
        "stream": True,
        "max_tokens": self.config.max_tokens,
        "temperature": self.config.temperature,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {self.config.api_key}",
    }

    async with self.client.stream(
        "POST",
        self.config.api_url,
        json=payload,
        headers=headers,
    ) as response:
        response.raise_for_status()

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
```

---

### 2.3 实现文本分句器

**文件：** `backend/services/text_splitter.py`

**功能：**
- 将流式文本按句子切分
- 支持中文标点（。！？，；）
- 缓冲机制处理不完整句子

**接口定义：**
```python
from typing import Generator, Optional
import re

class TextSplitter:
    """文本分句器"""

    # 句子结束标点
    SENTENCE_ENDINGS = ['。', '！', '？', '；', '…', '.', '!', '?', ';']

    # 逗号作为次要分割点（句子过长时）
    COMMA_MARKS = ['，', ',']

    # 单句最大长度（超过则在逗号处分割）
    MAX_SENTENCE_LENGTH = 50

    def __init__(self):
        self.buffer = ""

    def feed(self, text: str) -> Generator[str, None, None]:
        """
        输入文本片段，输出完整句子

        Args:
            text: 输入的文本片段

        Yields:
            完整的句子
        """
        self.buffer += text

        while True:
            sentence = self._try_extract_sentence()
            if sentence:
                yield sentence
            else:
                break

    def flush(self) -> Optional[str]:
        """
        刷新缓冲区，返回剩余文本

        Returns:
            剩余的文本（如果有）
        """
        if self.buffer.strip():
            result = self.buffer.strip()
            self.buffer = ""
            return result
        return None

    def _try_extract_sentence(self) -> Optional[str]:
        """尝试从缓冲区提取一个句子"""
        # 查找句子结束标点
        for i, char in enumerate(self.buffer):
            if char in self.SENTENCE_ENDINGS:
                sentence = self.buffer[:i+1].strip()
                self.buffer = self.buffer[i+1:]
                return sentence

            # 句子过长，在逗号处分割
            if i >= self.MAX_SENTENCE_LENGTH and char in self.COMMA_MARKS:
                sentence = self.buffer[:i+1].strip()
                self.buffer = self.buffer[i+1:]
                return sentence

        return None

    def reset(self):
        """重置缓冲区"""
        self.buffer = ""
```

**测试用例：**
```python
def test_text_splitter():
    splitter = TextSplitter()

    # 模拟流式输入
    chunks = ["我理解", "你的感受，", "能告诉我", "发生了什么吗？"]

    sentences = []
    for chunk in chunks:
        for sentence in splitter.feed(chunk):
            sentences.append(sentence)

    # 最后刷新
    final = splitter.flush()
    if final:
        sentences.append(final)

    assert sentences == ["我理解你的感受，", "能告诉我发生了什么吗？"]
```

---

### 2.4 实现 tts_chunk 同步下发

**文件：** `backend/services/stream_processor.py`

**功能：**
- 整合 LLM 流式输出 + 分句 + TTS
- 按句子生成 tts_chunk 消息

**接口定义：**
```python
from dataclasses import dataclass
from typing import AsyncGenerator, Callable, Awaitable
import asyncio

@dataclass
class TTSChunk:
    """TTS 片段"""
    text: str           # 文字内容
    audio: bytes        # MP3 音频
    seq: int            # 序号
    is_final: bool      # 是否最后一个

class StreamProcessor:
    """流式处理器：LLM + 分句 + TTS"""

    def __init__(
        self,
        llm_service: 'LLMService',
        tts_service: 'TTSService',
        emotion_parser: 'EmotionParser',
    ):
        self.llm_service = llm_service
        self.tts_service = tts_service
        self.emotion_parser = emotion_parser
        self.text_splitter = TextSplitter()

    async def process(
        self,
        messages: list[dict],
        on_emotion: Callable[[str], Awaitable[None]] = None,
    ) -> AsyncGenerator[TTSChunk, None]:
        """
        处理对话，流式返回 tts_chunk

        Args:
            messages: 对话历史
            on_emotion: 情感变化回调

        Yields:
            TTSChunk 对象
        """
        full_response = ""
        seq = 0

        # 流式获取 LLM 输出
        async for text_chunk in self.llm_service.chat_stream(messages):
            full_response += text_chunk

            # 分句
            for sentence in self.text_splitter.feed(text_chunk):
                seq += 1

                # 合成语音
                tts_result = await self.tts_service.synthesize(sentence)

                if tts_result.success:
                    yield TTSChunk(
                        text=sentence,
                        audio=tts_result.audio_data,
                        seq=seq,
                        is_final=False
                    )

        # 处理剩余文本
        remaining = self.text_splitter.flush()
        if remaining:
            seq += 1
            tts_result = await self.tts_service.synthesize(remaining)

            if tts_result.success:
                yield TTSChunk(
                    text=remaining,
                    audio=tts_result.audio_data,
                    seq=seq,
                    is_final=False
                )

        # 解析情感（从完整响应）
        parsed = self.emotion_parser.parse(full_response)
        if on_emotion and parsed.emotion:
            await on_emotion(parsed.emotion)

        # 发送最终标记
        yield TTSChunk(
            text="",
            audio=b"",
            seq=seq + 1,
            is_final=True
        )

    def reset(self):
        """重置状态"""
        self.text_splitter.reset()
```

---

### 2.5 更新 WebSocket 处理器

**文件：** `backend/api/websocket.py`（更新）

**更新功能：**
- 使用 StreamProcessor
- 发送 tts_chunk 消息

**更新代码：**
```python
import base64
from services.stream_processor import StreamProcessor, TTSChunk

class WebSocketHandler:
    # ... 已有代码 ...

    async def on_asr_complete(self, final_text: str):
        """ASR 识别完成回调"""
        # 发送 asr_end 消息
        await self.send_message({
            "type": "asr_end",
            "data": {"text": final_text}
        })

        # 添加用户消息到上下文
        self.context_manager.add_user_message(final_text)
        messages = self.context_manager.get_messages()

        # 流式处理
        full_text = ""
        async for chunk in self.stream_processor.process(
            messages,
            on_emotion=self._on_emotion_change
        ):
            if chunk.is_final:
                # 发送 tts_end
                await self.send_message({
                    "type": "tts_end",
                    "data": {"full_text": full_text}
                })
            else:
                full_text += chunk.text

                # 发送 tts_chunk
                await self.send_message({
                    "type": "tts_chunk",
                    "data": {
                        "text": chunk.text,
                        "audio": base64.b64encode(chunk.audio).decode('utf-8'),
                        "seq": chunk.seq,
                        "is_final": False
                    }
                })

        # 添加助手消息到上下文
        self.context_manager.add_assistant_message(full_text)

    async def _on_emotion_change(self, emotion: str):
        """情感变化回调"""
        if emotion != self.current_emotion:
            self.current_emotion = emotion
            await self.send_message({
                "type": "emotion",
                "data": {"emotion": emotion}
            })
```

---

### 2.6 前端音频播放队列

**文件：** `frontend/src/hooks/useAudioPlayer.ts`

**功能：**
- 管理音频播放队列
- 按顺序播放 MP3 片段
- 支持停止/清空队列

**接口定义：**
```typescript
import { useRef, useState, useCallback } from 'react';

interface AudioChunk {
  audio: string;  // Base64 encoded MP3
  seq: number;
}

interface UseAudioPlayerReturn {
  isPlaying: boolean;
  currentSeq: number;
  enqueue: (chunk: AudioChunk) => void;
  stop: () => void;
  clear: () => void;
}

export const useAudioPlayer = (): UseAudioPlayerReturn => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentSeq, setCurrentSeq] = useState(0);

  const queueRef = useRef<AudioChunk[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const isProcessingRef = useRef(false);
  const shouldStopRef = useRef(false);

  // 初始化 AudioContext
  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
    }
    return audioContextRef.current;
  }, []);

  // Base64 转 ArrayBuffer
  const base64ToArrayBuffer = (base64: string): ArrayBuffer => {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  };

  // 播放单个音频
  const playAudio = async (chunk: AudioChunk): Promise<void> => {
    const audioContext = getAudioContext();

    // 解码音频
    const arrayBuffer = base64ToArrayBuffer(chunk.audio);
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

    // 创建播放源
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);

    // 等待播放完成
    return new Promise((resolve) => {
      source.onended = () => resolve();
      source.start();
      setCurrentSeq(chunk.seq);
    });
  };

  // 处理队列
  const processQueue = useCallback(async () => {
    if (isProcessingRef.current) return;

    isProcessingRef.current = true;
    setIsPlaying(true);

    while (queueRef.current.length > 0 && !shouldStopRef.current) {
      const chunk = queueRef.current.shift()!;
      try {
        await playAudio(chunk);
      } catch (error) {
        console.error('Audio playback error:', error);
      }
    }

    isProcessingRef.current = false;
    setIsPlaying(false);
    shouldStopRef.current = false;
  }, []);

  // 入队
  const enqueue = useCallback((chunk: AudioChunk) => {
    queueRef.current.push(chunk);

    // 排序（确保按 seq 顺序）
    queueRef.current.sort((a, b) => a.seq - b.seq);

    // 开始处理
    if (!isProcessingRef.current) {
      processQueue();
    }
  }, [processQueue]);

  // 停止
  const stop = useCallback(() => {
    shouldStopRef.current = true;
  }, []);

  // 清空
  const clear = useCallback(() => {
    queueRef.current = [];
    shouldStopRef.current = true;
  }, []);

  return {
    isPlaying,
    currentSeq,
    enqueue,
    stop,
    clear,
  };
};
```

---

### 2.7 前端文字音频同步展示

**文件：** `frontend/src/hooks/useConversation.ts`（更新）

**更新功能：**
- 处理 tts_chunk 消息
- 文字追加 + 音频入队

**更新代码：**
```typescript
import { useState, useCallback, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAudioPlayer } from './useAudioPlayer';
import { useEmotion } from './useEmotion';

type Speaker = 'user' | 'assistant';

interface UseConversationReturn {
  text: string;
  speaker: Speaker;
  isStreaming: boolean;
  isPlaying: boolean;
}

export const useConversation = (): UseConversationReturn => {
  const [text, setText] = useState('');
  const [speaker, setSpeaker] = useState<Speaker>('user');
  const [isStreaming, setIsStreaming] = useState(false);

  const { onMessage } = useWebSocket();
  const { enqueue, clear, isPlaying } = useAudioPlayer();
  const { setEmotionFromServer } = useEmotion();

  useEffect(() => {
    const unsubscribe = onMessage((message) => {
      switch (message.type) {
        case 'asr_result':
          // ASR 流式识别结果
          setText(message.data.text);
          setSpeaker('user');
          setIsStreaming(!message.data.is_final);
          break;

        case 'asr_end':
          // ASR 识别完成
          setText(message.data.text);
          setSpeaker('user');
          setIsStreaming(false);
          break;

        case 'emotion':
          // 情感状态变化
          setEmotionFromServer(message.data.emotion);
          break;

        case 'tts_chunk':
          // TTS 文字+音频片段
          if (message.data.seq === 1) {
            // 第一个片段，清空之前的文字
            setText(message.data.text);
          } else {
            // 追加文字
            setText(prev => prev + message.data.text);
          }
          setSpeaker('assistant');
          setIsStreaming(true);

          // 音频入队
          if (message.data.audio) {
            enqueue({
              audio: message.data.audio,
              seq: message.data.seq,
            });
          }
          break;

        case 'tts_end':
          // TTS 完成
          setIsStreaming(false);
          break;

        case 'error':
          // 错误处理
          console.error('Server error:', message.data);
          setIsStreaming(false);
          break;
      }
    });

    return unsubscribe;
  }, [onMessage, enqueue, setEmotionFromServer]);

  return {
    text,
    speaker,
    isStreaming,
    isPlaying,
  };
};
```

---

### 2.8 更新 TextArea 组件

**文件：** `frontend/src/components/TextArea/TextArea.tsx`（更新）

**更新功能：**
- 流式文字追加显示
- 自动滚动到底部

**更新代码：**
```typescript
import React, { useEffect, useRef } from 'react';
import './TextArea.css';

type Speaker = 'user' | 'assistant';

interface TextAreaProps {
  text: string;
  speaker: Speaker;
  isStreaming: boolean;
  error?: {
    message: string;
    onRetry: () => void;
  };
}

export const TextArea: React.FC<TextAreaProps> = ({
  text,
  speaker,
  isStreaming,
  error,
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
      <div className="text-area text-area--error">
        <p className="error-message">{error.message}</p>
        <button className="retry-button" onClick={error.onRetry}>
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="text-area" ref={containerRef}>
      <p className={`text-content text-content--${speaker}`}>
        {text}
        {isStreaming && <span className="cursor">|</span>}
      </p>
    </div>
  );
};
```

**样式更新：** `frontend/src/components/TextArea/TextArea.css`
```css
.text-area {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow-y: auto;
  padding: 20px;
  box-sizing: border-box;
}

.text-content {
  font-size: 1.2rem;
  line-height: 1.8;
  text-align: center;
  max-width: 80%;
  word-wrap: break-word;
}

.text-content--user {
  color: #333;
}

.text-content--assistant {
  color: #2c5282;
}

/* 流式输出光标 */
.cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 错误状态 */
.text-area--error {
  flex-direction: column;
}

.error-message {
  color: #e53e3e;
  margin-bottom: 16px;
}

.retry-button {
  padding: 8px 24px;
  background-color: #e53e3e;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.retry-button:hover {
  background-color: #c53030;
}
```

---

## 3. 配置文件更新

**文件：** `backend/config/settings.py`（更新）

**新增配置：**
```python
class Settings(BaseSettings):
    # ... 已有配置 ...

    # 火山引擎 TTS 配置（新增）
    VOLC_TTS_APP_ID: str = ""
    VOLC_TTS_TOKEN: str = ""
    VOLC_TTS_CLUSTER: str = "volcano_tts"
    VOLC_TTS_VOICE_TYPE: str = "zh_female_cancan_mars_bigtts"
    VOLC_TTS_SPEED_RATIO: float = 1.0
    VOLC_TTS_VOLUME_RATIO: float = 1.0

    class Config:
        env_file = ".env"
```

**文件：** `backend/.env.example`（更新）

```
# 火山引擎 ASR
VOLC_ASR_APP_ID=your_app_id
VOLC_ASR_TOKEN=your_token

# 火山引擎 TTS（新增）
VOLC_TTS_APP_ID=your_app_id
VOLC_TTS_TOKEN=your_token
VOLC_TTS_CLUSTER=volcano_tts
VOLC_TTS_VOICE_TYPE=zh_female_cancan_mars_bigtts
VOLC_TTS_SPEED_RATIO=1.0
VOLC_TTS_VOLUME_RATIO=1.0

# DeepSeek LLM
DEEPSEEK_API_KEY=your_api_key
```

---

## 4. 测试计划

### 4.1 单元测试

| 测试对象 | 测试内容 | 文件 |
|----------|----------|------|
| TextSplitter | 分句逻辑 | `tests/test_text_splitter.py` |
| TTSService | TTS 调用（Mock） | `tests/test_tts_service.py` |
| StreamProcessor | 流式处理逻辑 | `tests/test_stream_processor.py` |
| useAudioPlayer | 播放队列逻辑 | `useAudioPlayer.test.ts` |

**TextSplitter 测试用例：**
```python
import pytest
from services.text_splitter import TextSplitter

class TestTextSplitter:
    def test_split_by_period(self):
        """句号分句"""
        splitter = TextSplitter()
        sentences = list(splitter.feed("你好。我是小马。"))
        assert sentences == ["你好。", "我是小马。"]

    def test_split_by_question(self):
        """问号分句"""
        splitter = TextSplitter()
        sentences = list(splitter.feed("你好吗？很好！"))
        assert sentences == ["你好吗？", "很好！"]

    def test_stream_input(self):
        """流式输入"""
        splitter = TextSplitter()
        result = []

        result.extend(splitter.feed("我理"))
        result.extend(splitter.feed("解你"))
        result.extend(splitter.feed("。谢谢"))

        final = splitter.flush()
        if final:
            result.append(final)

        assert result == ["我理解你。", "谢谢"]

    def test_long_sentence_split_at_comma(self):
        """长句在逗号处分割"""
        splitter = TextSplitter()
        splitter.MAX_SENTENCE_LENGTH = 10

        long_text = "这是一个非常非常长的句子，后面还有内容。"
        sentences = list(splitter.feed(long_text))

        # 应该在逗号处分割
        assert len(sentences) >= 2
```

**useAudioPlayer 测试用例：**
```typescript
import { renderHook, act } from '@testing-library/react';
import { useAudioPlayer } from './useAudioPlayer';

describe('useAudioPlayer', () => {
  it('should enqueue and track playing state', () => {
    const { result } = renderHook(() => useAudioPlayer());

    expect(result.current.isPlaying).toBe(false);

    // Mock audio context for testing
    // ...
  });

  it('should clear queue on stop', () => {
    const { result } = renderHook(() => useAudioPlayer());

    act(() => {
      result.current.clear();
    });

    expect(result.current.isPlaying).toBe(false);
  });
});
```

### 4.2 手工测试

| 测试项 | 验证内容 |
|--------|----------|
| 文字音频同步 | 说话后，文字流式出现，同时播放语音 |
| 分句正确 | 句子在标点处正确分割 |
| 播放顺序 | 多个片段按顺序播放，无重叠 |
| 长回复 | 长对话回复正常分段播放 |
| 错误处理 | TTS 失败时显示错误提示 |

**手工测试步骤：**
```bash
# 1. 启动后端
cd backend
uvicorn main:app --reload

# 2. 启动前端
cd frontend
npm run dev

# 3. 浏览器测试

# 测试 1: 基本同步
# - 说 "你好"
# - 验证：看到文字"你好"的同时听到语音

# 测试 2: 长回复
# - 说 "给我讲一个小故事"
# - 验证：文字分段显示，语音连续播放

# 测试 3: 快速对话
# - 连续说多句话
# - 验证：每次都能正确播放回复

# 测试 4: 网络延迟模拟
# - 使用开发者工具模拟慢网络
# - 验证：播放队列正确处理延迟到达的片段
```

---

## 5. 交付物

完成本阶段后，应具备：

- [ ] `backend/services/tts_service.py` - TTS 服务实现
- [ ] `backend/services/text_splitter.py` - 文本分句器实现
- [ ] `backend/services/stream_processor.py` - 流式处理器实现
- [ ] `backend/services/llm_service.py` - 更新流式调用
- [ ] `frontend/src/hooks/useAudioPlayer.ts` - 音频播放队列
- [ ] `frontend/src/hooks/useConversation.ts` - 更新 tts_chunk 处理
- [ ] 后端测试文件
- [ ] 文字和语音同步展示
- [ ] 分句合成正常工作
- [ ] 播放队列按顺序播放
- [ ] 单元测试全部通过

---

## 6. 预计产出文件

```
backend/
├── services/
│   ├── tts_service.py         # 新增
│   ├── text_splitter.py       # 新增
│   ├── stream_processor.py    # 新增
│   └── llm_service.py         # 更新（流式）
├── api/
│   └── websocket.py           # 更新
├── config/
│   └── settings.py            # 更新
├── tests/
│   ├── test_tts_service.py    # 新增
│   ├── test_text_splitter.py  # 新增
│   └── test_stream_processor.py # 新增
└── .env.example               # 更新

frontend/
└── src/
    ├── hooks/
    │   ├── useAudioPlayer.ts  # 新增
    │   └── useConversation.ts # 更新
    └── components/
        └── TextArea/
            ├── TextArea.tsx   # 更新
            └── TextArea.css   # 更新
```

---

## 7. 注意事项

### 7.1 音频播放兼容性
- 使用 Web Audio API 而非 `<audio>` 标签
- AudioContext 需要用户交互后才能创建（浏览器限制）
- 首次播放可能需要用户点击触发

### 7.2 分句策略
- 优先在句号、问号、感叹号处分割
- 句子过长时在逗号处分割
- 避免句子过短（单字不分句）

### 7.3 流式处理顺序
```
LLM 流式输出 → 分句器缓冲 → 完整句子 → TTS 合成 → tts_chunk 下发
```

### 7.4 情感解析时机
- LLM 完整响应才能解析情感标签
- 情感消息在 tts_chunk 之前或期间发送
- 头像切换不影响音频播放

### 7.5 错误恢复
- TTS 单句失败：跳过该句音频，文字仍然显示
- TTS 服务完全不可用：显示错误提示
