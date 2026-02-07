# 实现计划 - 阶段 6：完整流程 + 收尾

> 版本：1.0
> 更新日期：2026-02-07

## 阶段目标

实现打断功能、静默检测与耳朵闪动、会话存储（localStorage），完成端到端完整流程测试，确保所有功能正常协作。

**前置条件：** 阶段 5（TTS + 同步播放）已完成

---

## 1. 任务清单

| 序号 | 任务 | 类型 | 可单元测试 |
|------|------|------|-----------|
| 6.1 | 实现打断功能 | 前端+后端 | ✓ |
| 6.2 | 实现静默检测 | 前端 | ✓ |
| 6.3 | 实现耳朵图标闪动 | 前端 | ✓ |
| 6.4 | 实现会话存储（localStorage） | 前端 | ✓ |
| 6.5 | 页面刷新恢复会话 | 前端 | ✓ |
| 6.6 | 端到端完整测试 | 测试 | - |
| 6.7 | 错误处理完善 | 前端+后端 | ✓ |

---

## 2. 详细任务说明

### 2.1 实现打断功能

**功能描述：**
- 用户在 AI 播放语音时开始说话
- 前端立即停止音频播放，清空播放队列
- 发送 `interrupt` 消息给后端
- 后端停止 LLM/TTS 处理，返回 `tts_end`
- 开始新一轮 ASR 识别

#### 2.1.1 前端打断检测

**文件：** `frontend/src/hooks/useInterrupt.ts`

```typescript
import { useCallback, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAudioPlayer } from './useAudioPlayer';

interface UseInterruptReturn {
  triggerInterrupt: () => void;
  isInterrupting: boolean;
}

export const useInterrupt = (): UseInterruptReturn => {
  const { sendMessage } = useWebSocket();
  const { clear: clearAudioQueue, isPlaying } = useAudioPlayer();
  const isInterruptingRef = useRef(false);

  const triggerInterrupt = useCallback(() => {
    if (!isPlaying || isInterruptingRef.current) {
      return;
    }

    isInterruptingRef.current = true;

    // 1. 立即停止音频播放
    clearAudioQueue();

    // 2. 发送打断消息
    sendMessage({
      type: 'interrupt',
      data: {}
    });

    // 重置标记（延迟，避免重复触发）
    setTimeout(() => {
      isInterruptingRef.current = false;
    }, 500);
  }, [isPlaying, clearAudioQueue, sendMessage]);

  return {
    triggerInterrupt,
    isInterrupting: isInterruptingRef.current,
  };
};
```

#### 2.1.2 前端录音时检测打断

**文件：** `frontend/src/hooks/useAudioRecorder.ts`（更新）

```typescript
import { useInterrupt } from './useInterrupt';

export const useAudioRecorder = () => {
  const { triggerInterrupt } = useInterrupt();
  const { isPlaying } = useAudioPlayer();

  // ... 已有代码 ...

  const onAudioData = useCallback((pcmData: Int16Array) => {
    // 检测是否有有效语音（简单阈值检测）
    const hasVoice = detectVoice(pcmData);

    if (hasVoice && isPlaying) {
      // AI 正在播放时用户说话，触发打断
      triggerInterrupt();
    }

    // 发送音频数据
    sendAudioData(pcmData);
  }, [isPlaying, triggerInterrupt]);

  return {
    // ...
  };
};

// 简单的语音检测（基于音量阈值）
function detectVoice(pcmData: Int16Array, threshold = 500): boolean {
  let sum = 0;
  for (let i = 0; i < pcmData.length; i++) {
    sum += Math.abs(pcmData[i]);
  }
  const average = sum / pcmData.length;
  return average > threshold;
}
```

#### 2.1.3 后端打断处理

**文件：** `backend/api/websocket.py`（更新）

```python
class WebSocketHandler:
    def __init__(self, websocket: WebSocket):
        # ... 已有代码 ...
        self.is_processing = False
        self.should_interrupt = False

    async def handle_message(self, message: dict):
        msg_type = message.get("type")

        if msg_type == "interrupt":
            await self._handle_interrupt()
        # ... 其他消息处理 ...

    async def _handle_interrupt(self):
        """处理打断请求"""
        self.should_interrupt = True

        # 发送 tts_end 表示当前回复结束
        await self.send_message({
            "type": "tts_end",
            "data": {"full_text": "", "interrupted": True}
        })

    async def on_asr_complete(self, final_text: str):
        """ASR 识别完成回调（更新）"""
        # 重置打断标记
        self.should_interrupt = False
        self.is_processing = True

        # ... ASR 处理 ...

        # 流式处理（检查打断）
        full_text = ""
        async for chunk in self.stream_processor.process(
            messages,
            on_emotion=self._on_emotion_change
        ):
            # 检查是否被打断
            if self.should_interrupt:
                break

            if chunk.is_final:
                await self.send_message({
                    "type": "tts_end",
                    "data": {"full_text": full_text}
                })
            else:
                full_text += chunk.text
                await self.send_message({
                    "type": "tts_chunk",
                    "data": {
                        "text": chunk.text,
                        "audio": base64.b64encode(chunk.audio).decode('utf-8'),
                        "seq": chunk.seq,
                        "is_final": False
                    }
                })

        self.is_processing = False
```

---

### 2.2 实现静默检测

**文件：** `frontend/src/hooks/useSilenceDetection.ts`

**功能：**
- 检测用户是否静默（5秒无语音输入）
- 触发耳朵图标闪动

**技术规格（来自 technical_spec.md）：**
- 静默阈值：5秒无语音输入
- 闪动间隔：2秒闪一次
- 每组闪动次数：3次（共6秒）
- 组间间隔：10秒

```typescript
import { useState, useEffect, useRef, useCallback } from 'react';

interface UseSilenceDetectionReturn {
  isSilent: boolean;
  shouldBlink: boolean;
  resetSilenceTimer: () => void;
}

interface SilenceConfig {
  silenceThreshold: number;    // 静默阈值（毫秒）
  blinkInterval: number;       // 闪动间隔（毫秒）
  blinksPerGroup: number;      // 每组闪动次数
  groupInterval: number;       // 组间间隔（毫秒）
}

const DEFAULT_CONFIG: SilenceConfig = {
  silenceThreshold: 5000,      // 5秒
  blinkInterval: 2000,         // 2秒
  blinksPerGroup: 3,           // 3次
  groupInterval: 10000,        // 10秒
};

export const useSilenceDetection = (
  config: SilenceConfig = DEFAULT_CONFIG
): UseSilenceDetectionReturn => {
  const [isSilent, setIsSilent] = useState(false);
  const [shouldBlink, setShouldBlink] = useState(false);

  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const blinkTimerRef = useRef<NodeJS.Timeout | null>(null);
  const blinkCountRef = useRef(0);
  const lastActivityRef = useRef(Date.now());

  // 开始闪动
  const startBlinking = useCallback(() => {
    blinkCountRef.current = 0;

    const doBlink = () => {
      if (blinkCountRef.current < config.blinksPerGroup) {
        setShouldBlink(true);

        // 闪动持续时间（500ms）
        setTimeout(() => setShouldBlink(false), 500);

        blinkCountRef.current++;

        // 下一次闪动
        blinkTimerRef.current = setTimeout(doBlink, config.blinkInterval);
      } else {
        // 一组结束，等待组间间隔后开始下一组
        blinkCountRef.current = 0;
        blinkTimerRef.current = setTimeout(doBlink, config.groupInterval);
      }
    };

    doBlink();
  }, [config]);

  // 停止闪动
  const stopBlinking = useCallback(() => {
    if (blinkTimerRef.current) {
      clearTimeout(blinkTimerRef.current);
      blinkTimerRef.current = null;
    }
    setShouldBlink(false);
    blinkCountRef.current = 0;
  }, []);

  // 重置静默计时器
  const resetSilenceTimer = useCallback(() => {
    lastActivityRef.current = Date.now();

    // 停止闪动
    stopBlinking();
    setIsSilent(false);

    // 清除现有计时器
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
    }

    // 设置新的静默检测计时器
    silenceTimerRef.current = setTimeout(() => {
      setIsSilent(true);
      startBlinking();
    }, config.silenceThreshold);
  }, [config.silenceThreshold, startBlinking, stopBlinking]);

  // 初始化
  useEffect(() => {
    resetSilenceTimer();

    return () => {
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }
      stopBlinking();
    };
  }, [resetSilenceTimer, stopBlinking]);

  return {
    isSilent,
    shouldBlink,
    resetSilenceTimer,
  };
};
```

---

### 2.3 实现耳朵图标闪动

**文件：** `frontend/src/components/AvatarArea/EarIndicator.tsx`（更新）

```typescript
import React from 'react';
import './EarIndicator.css';

interface EarIndicatorProps {
  isBlinking: boolean;
  visible: boolean;
}

export const EarIndicator: React.FC<EarIndicatorProps> = ({
  isBlinking,
  visible,
}) => {
  if (!visible) {
    return null;
  }

  return (
    <span className={`ear-indicator ${isBlinking ? 'ear-indicator--blinking' : ''}`}>
      👂
    </span>
  );
};
```

**样式：** `frontend/src/components/AvatarArea/EarIndicator.css`

```css
.ear-indicator {
  position: absolute;
  top: 10%;
  right: 10%;
  font-size: 2rem;
  opacity: 0.8;
  transition: opacity 0.2s ease-in-out;
}

.ear-indicator--blinking {
  animation: ear-blink 0.5s ease-in-out;
}

@keyframes ear-blink {
  0% {
    opacity: 0.8;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
  100% {
    opacity: 0.8;
    transform: scale(1);
  }
}

/* 响应式调整 */
@media (max-width: 768px) {
  .ear-indicator {
    font-size: 1.5rem;
  }
}
```

**更新 AvatarArea 组件：**

**文件：** `frontend/src/components/AvatarArea/AvatarArea.tsx`（更新）

```typescript
import React from 'react';
import { EarIndicator } from './EarIndicator';
import { useSilenceDetection } from '../../hooks/useSilenceDetection';
import './AvatarArea.css';

type EmotionType = 'default' | 'empathy' | 'comfort' | 'happy';

const AVATAR_MAP: Record<EmotionType, string> = {
  default: '/assets/avatars/default.png',
  empathy: '/assets/avatars/empathy.png',
  comfort: '/assets/avatars/comfort.png',
  happy: '/assets/avatars/happy.png',
};

interface AvatarAreaProps {
  emotion: EmotionType;
  isListening: boolean;       // 是否正在录音
  isAISpeaking: boolean;      // AI 是否正在说话
  onUserActivity: () => void; // 用户活动回调
}

export const AvatarArea: React.FC<AvatarAreaProps> = ({
  emotion,
  isListening,
  isAISpeaking,
  onUserActivity,
}) => {
  const { shouldBlink, resetSilenceTimer } = useSilenceDetection();

  // 用户活动时重置计时器
  React.useEffect(() => {
    if (isListening) {
      resetSilenceTimer();
    }
  }, [isListening, resetSilenceTimer]);

  // 判断是否显示耳朵图标
  // 只在用户静默且 AI 没有说话时显示
  const showEarIndicator = !isListening && !isAISpeaking;

  return (
    <div className="avatar-area">
      <div className="avatar-container">
        <img
          className="avatar-image"
          src={AVATAR_MAP[emotion]}
          alt={`Avatar - ${emotion}`}
        />
        <EarIndicator
          isBlinking={shouldBlink}
          visible={showEarIndicator}
        />
      </div>
    </div>
  );
};
```

---

### 2.4 实现会话存储（localStorage）

**文件：** `frontend/src/services/storage.ts`

**功能：**
- 保存对话历史到 localStorage
- 页面刷新后恢复对话
- 管理上下文数据

```typescript
import { Message } from '../types/conversation';

const STORAGE_KEYS = {
  CONVERSATION_HISTORY: 'mapijing_conversation_history',
  CURRENT_EMOTION: 'mapijing_current_emotion',
  LAST_SESSION_TIME: 'mapijing_last_session_time',
};

// 最大存储条数（防止 localStorage 超限）
const MAX_HISTORY_LENGTH = 100;

export interface ConversationHistory {
  messages: Message[];
  currentEmotion: string;
  lastUpdated: number;
}

export const storage = {
  /**
   * 保存对话历史
   */
  saveConversation(history: ConversationHistory): void {
    try {
      // 限制消息数量
      const trimmedMessages = history.messages.slice(-MAX_HISTORY_LENGTH);

      const data: ConversationHistory = {
        messages: trimmedMessages,
        currentEmotion: history.currentEmotion,
        lastUpdated: Date.now(),
      };

      localStorage.setItem(
        STORAGE_KEYS.CONVERSATION_HISTORY,
        JSON.stringify(data)
      );
    } catch (error) {
      console.error('Failed to save conversation:', error);
      // localStorage 可能已满，尝试清理旧数据
      this.clearOldData();
    }
  },

  /**
   * 加载对话历史
   */
  loadConversation(): ConversationHistory | null {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.CONVERSATION_HISTORY);
      if (!data) {
        return null;
      }

      const history: ConversationHistory = JSON.parse(data);

      // 验证数据结构
      if (!Array.isArray(history.messages)) {
        return null;
      }

      return history;
    } catch (error) {
      console.error('Failed to load conversation:', error);
      return null;
    }
  },

  /**
   * 添加单条消息
   */
  addMessage(message: Message): void {
    const history = this.loadConversation() || {
      messages: [],
      currentEmotion: '默认陪伴',
      lastUpdated: Date.now(),
    };

    history.messages.push(message);
    this.saveConversation(history);
  },

  /**
   * 更新当前情感状态
   */
  updateEmotion(emotion: string): void {
    const history = this.loadConversation();
    if (history) {
      history.currentEmotion = emotion;
      this.saveConversation(history);
    }
  },

  /**
   * 清空对话历史
   */
  clearConversation(): void {
    localStorage.removeItem(STORAGE_KEYS.CONVERSATION_HISTORY);
  },

  /**
   * 清理旧数据（localStorage 空间不足时）
   */
  clearOldData(): void {
    const history = this.loadConversation();
    if (history && history.messages.length > 10) {
      // 保留最近 10 条
      history.messages = history.messages.slice(-10);
      this.saveConversation(history);
    }
  },

  /**
   * 获取存储使用情况
   */
  getStorageUsage(): { used: number; total: number } {
    let used = 0;
    for (const key in localStorage) {
      if (localStorage.hasOwnProperty(key)) {
        used += localStorage.getItem(key)?.length || 0;
      }
    }
    // localStorage 通常限制为 5MB
    return { used, total: 5 * 1024 * 1024 };
  },
};
```

**类型定义：** `frontend/src/types/conversation.ts`

```typescript
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  emotion?: string;  // 仅 assistant 消息有
}

export interface ConversationState {
  messages: Message[];
  currentEmotion: string;
  isLoading: boolean;
}
```

---

### 2.5 页面刷新恢复会话

**文件：** `frontend/src/hooks/useConversation.ts`（更新）

**新增功能：**
- 页面加载时恢复对话历史
- 每次对话后保存到 localStorage

```typescript
import { useState, useEffect, useCallback } from 'react';
import { storage, ConversationHistory } from '../services/storage';
import { Message } from '../types/conversation';
import { v4 as uuidv4 } from 'uuid';

export const useConversation = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentText, setCurrentText] = useState('');
  const [speaker, setSpeaker] = useState<'user' | 'assistant'>('user');
  const [isStreaming, setIsStreaming] = useState(false);

  const { setEmotionFromServer, emotion } = useEmotion();
  const { onMessage, sendMessage } = useWebSocket();
  const { enqueue, clear: clearAudio, isPlaying } = useAudioPlayer();

  // 页面加载时恢复对话
  useEffect(() => {
    const history = storage.loadConversation();
    if (history) {
      setMessages(history.messages);
      setEmotionFromServer(history.currentEmotion);
    }
  }, []);

  // 添加用户消息
  const addUserMessage = useCallback((text: string) => {
    const message: Message = {
      id: uuidv4(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };

    setMessages(prev => {
      const updated = [...prev, message];
      // 保存到 localStorage
      storage.saveConversation({
        messages: updated,
        currentEmotion: emotion,
        lastUpdated: Date.now(),
      });
      return updated;
    });
  }, [emotion]);

  // 添加助手消息
  const addAssistantMessage = useCallback((text: string, msgEmotion: string) => {
    const message: Message = {
      id: uuidv4(),
      role: 'assistant',
      content: text,
      timestamp: Date.now(),
      emotion: msgEmotion,
    };

    setMessages(prev => {
      const updated = [...prev, message];
      // 保存到 localStorage
      storage.saveConversation({
        messages: updated,
        currentEmotion: msgEmotion,
        lastUpdated: Date.now(),
      });
      return updated;
    });
  }, []);

  // 处理 WebSocket 消息
  useEffect(() => {
    let currentAssistantText = '';

    const unsubscribe = onMessage((message) => {
      switch (message.type) {
        case 'asr_result':
          setCurrentText(message.data.text);
          setSpeaker('user');
          setIsStreaming(!message.data.is_final);
          break;

        case 'asr_end':
          setCurrentText(message.data.text);
          setSpeaker('user');
          setIsStreaming(false);
          // 保存用户消息
          addUserMessage(message.data.text);
          break;

        case 'emotion':
          setEmotionFromServer(message.data.emotion);
          storage.updateEmotion(message.data.emotion);
          break;

        case 'tts_chunk':
          if (message.data.seq === 1) {
            currentAssistantText = message.data.text;
            setCurrentText(message.data.text);
          } else {
            currentAssistantText += message.data.text;
            setCurrentText(prev => prev + message.data.text);
          }
          setSpeaker('assistant');
          setIsStreaming(true);

          if (message.data.audio) {
            enqueue({
              audio: message.data.audio,
              seq: message.data.seq,
            });
          }
          break;

        case 'tts_end':
          setIsStreaming(false);
          // 保存助手消息（如果不是被打断的）
          if (!message.data.interrupted && currentAssistantText) {
            addAssistantMessage(currentAssistantText, emotion);
          }
          currentAssistantText = '';
          break;

        case 'error':
          console.error('Server error:', message.data);
          setIsStreaming(false);
          break;
      }
    });

    return unsubscribe;
  }, [onMessage, enqueue, setEmotionFromServer, addUserMessage, addAssistantMessage, emotion]);

  // 清空对话历史
  const clearHistory = useCallback(() => {
    setMessages([]);
    storage.clearConversation();
  }, []);

  return {
    messages,
    currentText,
    speaker,
    isStreaming,
    isPlaying,
    clearHistory,
  };
};
```

---

### 2.6 后端同步上下文

**文件：** `backend/api/websocket.py`（更新）

**说明：** 后端不保存对话历史，但需要在 WebSocket 连接期间维护上下文。

```python
class WebSocketHandler:
    async def handle_restore_context(self, messages: list[dict]):
        """
        恢复对话上下文（可选功能）

        如果需要后端也同步历史，前端可以在连接建立时发送历史消息
        """
        for msg in messages:
            if msg["role"] == "user":
                self.context_manager.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                self.context_manager.add_assistant_message(msg["content"])
```

**前端连接时恢复上下文（可选）：**

```typescript
// frontend/src/hooks/useWebSocket.ts（更新）

const onConnect = useCallback(() => {
  // 连接建立后，发送历史消息恢复上下文
  const history = storage.loadConversation();
  if (history && history.messages.length > 0) {
    sendMessage({
      type: 'restore_context',
      data: {
        messages: history.messages.map(m => ({
          role: m.role,
          content: m.content,
        }))
      }
    });
  }
}, [sendMessage]);
```

---

### 2.7 错误处理完善

#### 2.7.1 前端错误处理

**文件：** `frontend/src/hooks/useErrorHandler.ts`

```typescript
import { useState, useCallback } from 'react';

interface ErrorInfo {
  code: string;
  message: string;
  retryable: boolean;
}

const ERROR_MESSAGES: Record<string, string> = {
  ASR_ERROR: '语音识别服务暂时不可用',
  LLM_ERROR: '对话服务暂时不可用',
  TTS_ERROR: '语音合成服务暂时不可用',
  NETWORK_ERROR: '网络连接失败',
  UNKNOWN_ERROR: '发生未知错误',
};

interface UseErrorHandlerReturn {
  error: ErrorInfo | null;
  setError: (error: ErrorInfo | null) => void;
  handleServerError: (errorData: { code: string; message?: string }) => void;
  clearError: () => void;
  retry: () => void;
}

export const useErrorHandler = (
  onRetry?: () => void
): UseErrorHandlerReturn => {
  const [error, setError] = useState<ErrorInfo | null>(null);

  const handleServerError = useCallback((errorData: { code: string; message?: string }) => {
    const message = errorData.message || ERROR_MESSAGES[errorData.code] || ERROR_MESSAGES.UNKNOWN_ERROR;

    setError({
      code: errorData.code,
      message,
      retryable: ['ASR_ERROR', 'LLM_ERROR', 'TTS_ERROR', 'NETWORK_ERROR'].includes(errorData.code),
    });
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const retry = useCallback(() => {
    clearError();
    onRetry?.();
  }, [clearError, onRetry]);

  return {
    error,
    setError,
    handleServerError,
    clearError,
    retry,
  };
};
```

#### 2.7.2 后端错误处理

**文件：** `backend/utils/error_handler.py`

```python
from enum import Enum
from typing import Optional
from dataclasses import dataclass

class ErrorCode(Enum):
    ASR_ERROR = "ASR_ERROR"
    LLM_ERROR = "LLM_ERROR"
    TTS_ERROR = "TTS_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

@dataclass
class AppError:
    code: ErrorCode
    message: str
    details: Optional[str] = None

def create_error_message(error: AppError) -> dict:
    """创建错误消息"""
    return {
        "type": "error",
        "data": {
            "code": error.code.value,
            "message": error.message,
        }
    }

# WebSocket 处理器中使用
async def safe_process(self, coro, error_code: ErrorCode, error_message: str):
    """安全执行异步操作，捕获错误"""
    try:
        return await coro
    except Exception as e:
        error = AppError(
            code=error_code,
            message=error_message,
            details=str(e)
        )
        await self.send_message(create_error_message(error))
        return None
```

---

### 2.8 主应用整合

**文件：** `frontend/src/App.tsx`（最终版）

```typescript
import React from 'react';
import { Layout } from './components/Layout/Layout';
import { AvatarArea } from './components/AvatarArea/AvatarArea';
import { TextArea } from './components/TextArea/TextArea';
import { useConversation } from './hooks/useConversation';
import { useEmotion } from './hooks/useEmotion';
import { useAudioRecorder } from './hooks/useAudioRecorder';
import { useErrorHandler } from './hooks/useErrorHandler';
import './styles/global.css';

const App: React.FC = () => {
  const {
    currentText,
    speaker,
    isStreaming,
    isPlaying,
  } = useConversation();

  const { emotion } = useEmotion();
  const { isRecording, startRecording, stopRecording } = useAudioRecorder();
  const { error, retry, clearError } = useErrorHandler(() => {
    // 重试逻辑：重新开始录音
    startRecording();
  });

  // 映射情感类型
  const emotionType = React.useMemo(() => {
    const map: Record<string, 'default' | 'empathy' | 'comfort' | 'happy'> = {
      '默认陪伴': 'default',
      '共情倾听': 'empathy',
      '安慰支持': 'comfort',
      '轻松愉悦': 'happy',
    };
    return map[emotion] || 'default';
  }, [emotion]);

  return (
    <Layout
      avatarArea={
        <AvatarArea
          emotion={emotionType}
          isListening={isRecording}
          isAISpeaking={isPlaying}
          onUserActivity={clearError}
        />
      }
      textArea={
        <TextArea
          text={currentText}
          speaker={speaker}
          isStreaming={isStreaming}
          error={error ? {
            message: error.message,
            onRetry: retry,
          } : undefined}
        />
      }
    />
  );
};

export default App;
```

---

## 3. 测试计划

### 3.1 单元测试

| 测试对象 | 测试内容 | 文件 |
|----------|----------|------|
| useInterrupt | 打断触发逻辑 | `useInterrupt.test.ts` |
| useSilenceDetection | 静默检测、闪动时序 | `useSilenceDetection.test.ts` |
| storage | localStorage 读写 | `storage.test.ts` |
| useErrorHandler | 错误处理逻辑 | `useErrorHandler.test.ts` |

**useSilenceDetection 测试用例：**
```typescript
import { renderHook, act } from '@testing-library/react';
import { useSilenceDetection } from './useSilenceDetection';

describe('useSilenceDetection', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should not blink initially', () => {
    const { result } = renderHook(() => useSilenceDetection());
    expect(result.current.shouldBlink).toBe(false);
  });

  it('should start blinking after silence threshold', () => {
    const { result } = renderHook(() => useSilenceDetection({
      silenceThreshold: 5000,
      blinkInterval: 2000,
      blinksPerGroup: 3,
      groupInterval: 10000,
    }));

    // 等待 5 秒
    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(result.current.isSilent).toBe(true);
  });

  it('should reset on user activity', () => {
    const { result } = renderHook(() => useSilenceDetection());

    // 等待进入静默状态
    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(result.current.isSilent).toBe(true);

    // 重置
    act(() => {
      result.current.resetSilenceTimer();
    });

    expect(result.current.isSilent).toBe(false);
    expect(result.current.shouldBlink).toBe(false);
  });
});
```

**storage 测试用例：**
```typescript
import { storage } from './storage';

describe('storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should save and load conversation', () => {
    const history = {
      messages: [
        { id: '1', role: 'user' as const, content: '你好', timestamp: Date.now() },
      ],
      currentEmotion: '默认陪伴',
      lastUpdated: Date.now(),
    };

    storage.saveConversation(history);
    const loaded = storage.loadConversation();

    expect(loaded).not.toBeNull();
    expect(loaded!.messages.length).toBe(1);
    expect(loaded!.messages[0].content).toBe('你好');
  });

  it('should clear conversation', () => {
    storage.saveConversation({
      messages: [],
      currentEmotion: '默认陪伴',
      lastUpdated: Date.now(),
    });

    storage.clearConversation();
    const loaded = storage.loadConversation();

    expect(loaded).toBeNull();
  });
});
```

### 3.2 端到端测试

| 测试场景 | 验证内容 |
|----------|----------|
| 完整对话流程 | 录音 → ASR → LLM → TTS → 播放 全链路 |
| 打断功能 | AI 说话时用户打断，立即停止 |
| 静默闪动 | 5秒无操作，耳朵开始闪动 |
| 会话恢复 | 刷新页面后对话历史恢复 |
| 多轮对话 | 连续多轮对话，上下文正确 |
| 错误恢复 | 模拟服务不可用，显示错误并重试 |

**端到端测试脚本：**
```bash
# 1. 启动后端
cd backend
uvicorn main:app --reload --port 8000

# 2. 启动前端
cd frontend
npm run dev

# 3. 浏览器手工测试

# 测试 1: 完整对话流程
# - 打开页面
# - 允许麦克风权限
# - 说 "你好"
# - 验证：
#   - 看到 "你好" 文字
#   - 收到 AI 回复（文字+语音同步）
#   - 头像根据情感切换

# 测试 2: 打断功能
# - 说一句话，等待 AI 回复
# - AI 回复过程中再次说话
# - 验证：
#   - AI 语音立即停止
#   - 开始识别新的语音输入

# 测试 3: 静默检测
# - 停止说话，等待 5 秒
# - 验证：
#   - 耳朵图标开始闪动
#   - 闪动模式：2秒一次，3次为一组
# - 再次说话
# - 验证：闪动立即停止

# 测试 4: 会话恢复
# - 进行几轮对话
# - 刷新页面
# - 验证：
#   - 对话历史恢复
#   - 情感状态恢复
#   - 可以继续对话

# 测试 5: 错误处理
# - 断开后端服务
# - 尝试说话
# - 验证：
#   - 显示错误提示
#   - 显示重试按钮
# - 恢复后端服务
# - 点击重试
# - 验证：功能恢复正常
```

---

## 4. 交付物

完成本阶段后，应具备：

- [ ] `frontend/src/hooks/useInterrupt.ts` - 打断功能 Hook
- [ ] `frontend/src/hooks/useSilenceDetection.ts` - 静默检测 Hook
- [ ] `frontend/src/services/storage.ts` - localStorage 封装
- [ ] `frontend/src/hooks/useErrorHandler.ts` - 错误处理 Hook
- [ ] `backend/utils/error_handler.py` - 后端错误处理
- [ ] 打断功能正常工作
- [ ] 静默检测触发耳朵闪动
- [ ] 会话刷新后可恢复
- [ ] 错误提示和重试功能
- [ ] 端到端完整流程测试通过
- [ ] 单元测试全部通过

---

## 5. 预计产出文件

```
frontend/
├── src/
│   ├── hooks/
│   │   ├── useInterrupt.ts          # 新增
│   │   ├── useSilenceDetection.ts   # 新增
│   │   ├── useErrorHandler.ts       # 新增
│   │   ├── useConversation.ts       # 更新
│   │   └── useAudioRecorder.ts      # 更新
│   ├── services/
│   │   └── storage.ts               # 新增
│   ├── components/
│   │   ├── AvatarArea/
│   │   │   ├── AvatarArea.tsx       # 更新
│   │   │   ├── EarIndicator.tsx     # 更新
│   │   │   └── EarIndicator.css     # 更新
│   │   └── TextArea/
│   │       └── TextArea.tsx         # 更新
│   ├── types/
│   │   └── conversation.ts          # 新增
│   └── App.tsx                      # 更新
│
├── __tests__/
│   ├── useInterrupt.test.ts         # 新增
│   ├── useSilenceDetection.test.ts  # 新增
│   ├── storage.test.ts              # 新增
│   └── useErrorHandler.test.ts      # 新增

backend/
├── api/
│   └── websocket.py                 # 更新
└── utils/
    └── error_handler.py             # 新增
```

---

## 6. 项目完成检查清单

完成所有阶段后，进行最终检查：

### 6.1 功能检查

| 功能 | 状态 |
|------|------|
| 响应式布局（手机/电脑） | [ ] |
| 虚拟人头像展示（4种状态） | [ ] |
| 情感状态切换 | [ ] |
| 语音录音 + PCM 采集 | [ ] |
| ASR 流式识别 | [ ] |
| LLM 对话（多轮上下文） | [ ] |
| TTS 语音合成 | [ ] |
| 文字音频同步展示 | [ ] |
| 打断功能 | [ ] |
| 静默检测 + 耳朵闪动 | [ ] |
| 会话存储和恢复 | [ ] |
| 错误提示和重试 | [ ] |

### 6.2 技术指标检查

| 指标 | 要求 | 状态 |
|------|------|------|
| 上下文长度限制 | 50k tokens | [ ] |
| 静默阈值 | 5秒 | [ ] |
| 闪动间隔 | 2秒 | [ ] |
| 每组闪动次数 | 3次 | [ ] |
| 组间间隔 | 10秒 | [ ] |
| 音频格式（上行） | PCM 16bit 16kHz | [ ] |
| 音频格式（下行） | MP3 | [ ] |

### 6.3 测试检查

| 测试类型 | 状态 |
|----------|------|
| 前端单元测试全部通过 | [ ] |
| 后端单元测试全部通过 | [ ] |
| 端到端完整流程测试 | [ ] |
| 响应式布局测试（手机/电脑） | [ ] |
| 长时间运行稳定性测试 | [ ] |

---

## 7. 注意事项

### 7.1 打断功能注意点
- 检测用户语音需要有阈值，避免噪音误触发
- 打断后需要等待一小段时间才能再次打断
- 后端收到打断后要立即停止处理

### 7.2 静默检测注意点
- AI 说话时不计入静默时间
- 用户录音时重置静默计时器
- 闪动动画要平滑，不能突兀

### 7.3 localStorage 注意点
- 5MB 限制，需要控制存储大小
- 存储失败时要有降级处理
- 数据格式版本化，便于后续升级

### 7.4 浏览器兼容性
- AudioContext 需要用户交互后创建
- 麦克风权限在非 HTTPS 下可能受限
- 测试主流浏览器（Chrome、Firefox、Safari）
