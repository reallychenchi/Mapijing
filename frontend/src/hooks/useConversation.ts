/**
 * 会话管理 Hook
 * 整合录音、WebSocket、ASR 结果处理、TTS 音频播放、会话存储
 */

import { useState, useCallback, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAudioRecorder } from './useAudioRecorder';
import { useMediaPermission } from './useMediaPermission';
import { useEmotion } from './useEmotion';
import { useAudioPlayer } from './useAudioPlayer';
import { storage } from '../services/storage';
import type { Message } from '../types/conversation';
import type {
  ServerMessage,
  AsrResultMessage,
  AsrEndMessage,
  EmotionMessage,
  LlmResponseMessage,
  TtsChunkMessage,
  TtsEndMessage,
} from '../types/message';
import {
  createAudioDataMessage,
  createAudioEndMessage,
  createInterruptMessage,
} from '../types/message';
import type { EmotionType } from '../types/emotion';

// 简单的唯一 ID 生成器
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export type ConversationState = 'idle' | 'listening' | 'processing' | 'speaking';

export type Speaker = 'user' | 'assistant';

export interface UseConversationReturn {
  // 状态
  state: ConversationState;
  permissionState: 'prompt' | 'granted' | 'denied' | 'checking';
  isConnected: boolean;

  // ASR 结果
  currentText: string; // 当前识别文本（实时更新）
  finalText: string; // 最终确认文本

  // LLM 回复
  assistantText: string; // 助手回复文本
  speaker: Speaker; // 当前说话者
  isStreaming: boolean; // 是否正在流式输出

  // 音频播放
  isPlaying: boolean; // 是否正在播放

  // 情感状态
  emotion: EmotionType;

  // 历史消息
  messages: Message[];

  // 操作
  startListening: () => Promise<void>;
  stopListening: () => void;
  requestPermission: () => Promise<boolean>;
  interrupt: () => void;
  clearHistory: () => void;

  // 错误
  error: string | null;
  clearError: () => void;
}

export function useConversation(): UseConversationReturn {
  const [state, setState] = useState<ConversationState>('idle');
  const [currentText, setCurrentText] = useState('');
  const [finalText, setFinalText] = useState('');
  const [assistantText, setAssistantText] = useState('');
  const [speaker, setSpeaker] = useState<Speaker>('user');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 使用惰性初始化来恢复对话历史
  const [messages, setMessages] = useState<Message[]>(() => {
    const history = storage.loadConversation();
    return history?.messages ?? [];
  });

  const isStoppingRef = useRef(false);
  const currentAssistantTextRef = useRef('');

  // 权限管理
  const { state: permissionState, request: requestPermission } = useMediaPermission();

  // 情感状态管理
  const { emotion, setEmotionFromServer } = useEmotion();

  // 音频播放管理
  const { enqueue, clear: clearAudio, isPlaying } = useAudioPlayer();

  // 添加用户消息到历史
  const addUserMessage = useCallback((text: string) => {
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };

    setMessages((prev) => {
      const updated = [...prev, userMessage];
      // 保存到 localStorage
      storage.saveConversation({
        messages: updated,
        currentEmotion: '默认陪伴',
        lastUpdated: Date.now(),
      });
      return updated;
    });
  }, []);

  // 添加助手消息到历史
  const addAssistantMessage = useCallback((text: string, msgEmotion?: string) => {
    const assistantMessage: Message = {
      id: generateId(),
      role: 'assistant',
      content: text,
      timestamp: Date.now(),
      emotion: msgEmotion,
    };

    setMessages((prev) => {
      const updated = [...prev, assistantMessage];
      // 保存到 localStorage
      storage.saveConversation({
        messages: updated,
        currentEmotion: msgEmotion || '默认陪伴',
        lastUpdated: Date.now(),
      });
      return updated;
    });
  }, []);

  // 处理服务端消息
  const handleServerMessage = useCallback(
    (message: ServerMessage) => {
      if (message.type === 'asr_result') {
        const asrMessage = message as AsrResultMessage;
        setCurrentText(asrMessage.data.text);
        setSpeaker('user');
        if (asrMessage.data.is_final) {
          setFinalText(asrMessage.data.text);
        }
      } else if (message.type === 'asr_end') {
        const asrEndMessage = message as AsrEndMessage;
        setFinalText(asrEndMessage.data.text);
        // 保存用户消息到历史
        if (asrEndMessage.data.text) {
          addUserMessage(asrEndMessage.data.text);
        }
        // 不立即切换到 idle，等待 TTS 回复
        setState('processing');
      } else if (message.type === 'emotion') {
        const emotionMessage = message as EmotionMessage;
        setEmotionFromServer(emotionMessage.data.emotion);
        storage.updateEmotion(emotionMessage.data.emotion);
      } else if (message.type === 'llm_response') {
        // 阶段4兼容：非流式 LLM 响应
        const llmMessage = message as LlmResponseMessage;
        setAssistantText(llmMessage.data.text);
        setSpeaker('assistant');
        setIsStreaming(false);
        setState('idle');
        // 保存助手消息
        addAssistantMessage(llmMessage.data.text);
      } else if (message.type === 'tts_chunk') {
        // 阶段5：TTS 文字+音频片段
        const ttsMessage = message as TtsChunkMessage;
        if (ttsMessage.data.seq === 1) {
          // 第一个片段，清空之前的文字
          setAssistantText(ttsMessage.data.text);
          currentAssistantTextRef.current = ttsMessage.data.text;
        } else {
          // 追加文字
          setAssistantText((prev) => prev + ttsMessage.data.text);
          currentAssistantTextRef.current += ttsMessage.data.text;
        }
        setSpeaker('assistant');
        setIsStreaming(true);
        setState('speaking');

        // 音频入队
        if (ttsMessage.data.audio) {
          enqueue({
            audio: ttsMessage.data.audio,
            seq: ttsMessage.data.seq,
          });
        }
      } else if (message.type === 'tts_end') {
        // TTS 完成
        const ttsEndMessage = message as TtsEndMessage;
        const fullText = ttsEndMessage.data.full_text || currentAssistantTextRef.current;
        if (fullText) {
          // 更新为完整文本
          setAssistantText(fullText);
          // 保存助手消息（如果有内容且不是被打断的）
          if (fullText.trim()) {
            addAssistantMessage(fullText);
          }
        }
        setIsStreaming(false);
        setState('idle');
        currentAssistantTextRef.current = '';
      }
    },
    [setEmotionFromServer, enqueue, addUserMessage, addAssistantMessage]
  );

  // WebSocket 连接
  const {
    state: wsState,
    send,
    error: wsError,
    clearError: clearWsError,
  } = useWebSocket({
    autoConnect: true,
    onMessage: handleServerMessage,
    onError: (err) => {
      setError(err.data.message);
      setState('idle');
    },
  });

  // 处理音频数据
  const handleAudioData = useCallback(
    (base64Audio: string, seq: number) => {
      if (wsState === 'connected') {
        send(createAudioDataMessage(base64Audio, seq));
      }
    },
    [wsState, send]
  );

  // 处理录音错误
  const handleRecorderError = useCallback((errorMsg: string) => {
    setError(errorMsg);
    setState('idle');
  }, []);

  // 录音管理
  const { start: startRecording, stop: stopRecording } = useAudioRecorder({
    onAudioData: handleAudioData,
    onError: handleRecorderError,
  });

  // 开始监听
  const startListening = useCallback(async () => {
    if (state !== 'idle') return;
    if (wsState !== 'connected') {
      setError('WebSocket 未连接');
      return;
    }

    setError(null);
    setCurrentText('');
    setFinalText('');
    isStoppingRef.current = false;

    setState('listening');
    await startRecording();
  }, [state, wsState, startRecording]);

  // 停止监听
  const stopListening = useCallback(() => {
    if (state !== 'listening' || isStoppingRef.current) return;

    isStoppingRef.current = true;
    stopRecording();
    setState('processing');

    // 发送音频结束消息
    if (wsState === 'connected') {
      send(createAudioEndMessage());
    }
  }, [state, wsState, stopRecording, send]);

  // 打断（用户开始说话时调用）
  const interrupt = useCallback(() => {
    if (state !== 'speaking') return;

    // 清空音频队列
    clearAudio();

    // 发送打断消息
    if (wsState === 'connected') {
      send(createInterruptMessage());
    }

    setState('idle');
    setIsStreaming(false);
  }, [state, wsState, send, clearAudio]);

  // 清除错误
  const clearError = useCallback(() => {
    setError(null);
    clearWsError();
  }, [clearWsError]);

  // 清空对话历史
  const clearHistory = useCallback(() => {
    setMessages([]);
    storage.clearConversation();
  }, []);

  // 计算实际的错误状态 - 直接使用 wsError 而不是通过 effect 同步
  const actualError = wsError ? wsError.data.message : error;

  return {
    state,
    permissionState,
    isConnected: wsState === 'connected',
    currentText,
    finalText,
    assistantText,
    speaker,
    isStreaming,
    isPlaying,
    emotion,
    messages,
    startListening,
    stopListening,
    requestPermission,
    clearHistory,
    interrupt,
    error: actualError,
    clearError,
  };
}
