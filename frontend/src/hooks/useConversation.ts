/**
 * 会话管理 Hook
 * 整合录音、WebSocket、ASR 结果处理
 */

import { useState, useCallback, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAudioRecorder } from './useAudioRecorder';
import { useMediaPermission } from './useMediaPermission';
import { useEmotion } from './useEmotion';
import type {
  ServerMessage,
  AsrResultMessage,
  AsrEndMessage,
  EmotionMessage,
  LlmResponseMessage,
} from '../types/message';
import { createAudioDataMessage, createAudioEndMessage } from '../types/message';
import type { EmotionType } from '../types/emotion';

export type ConversationState = 'idle' | 'listening' | 'processing';

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

  // 情感状态
  emotion: EmotionType;

  // 操作
  startListening: () => Promise<void>;
  stopListening: () => void;
  requestPermission: () => Promise<boolean>;

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
  const [error, setError] = useState<string | null>(null);

  const isStoppingRef = useRef(false);

  // 权限管理
  const { state: permissionState, request: requestPermission } = useMediaPermission();

  // 情感状态管理
  const { emotion, setEmotionFromServer } = useEmotion();

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
        // 不立即切换到 idle，等待 LLM 回复
        setState('processing');
      } else if (message.type === 'emotion') {
        const emotionMessage = message as EmotionMessage;
        setEmotionFromServer(emotionMessage.data.emotion);
      } else if (message.type === 'llm_response') {
        const llmMessage = message as LlmResponseMessage;
        setAssistantText(llmMessage.data.text);
        setSpeaker('assistant');
        setState('idle');
      }
    },
    [setEmotionFromServer]
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

  // 清除错误
  const clearError = useCallback(() => {
    setError(null);
    clearWsError();
  }, [clearWsError]);

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
    emotion,
    startListening,
    stopListening,
    requestPermission,
    error: actualError,
    clearError,
  };
}
