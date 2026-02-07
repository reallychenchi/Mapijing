/**
 * 会话管理 Hook
 * 整合录音、WebSocket、ASR 结果处理
 */

import { useState, useCallback, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAudioRecorder } from './useAudioRecorder';
import { useMediaPermission } from './useMediaPermission';
import type { ServerMessage, AsrResultMessage, AsrEndMessage } from '../types/message';
import { createAudioDataMessage, createAudioEndMessage } from '../types/message';

export type ConversationState = 'idle' | 'listening' | 'processing';

export interface UseConversationReturn {
  // 状态
  state: ConversationState;
  permissionState: 'prompt' | 'granted' | 'denied' | 'checking';
  isConnected: boolean;

  // ASR 结果
  currentText: string; // 当前识别文本（实时更新）
  finalText: string; // 最终确认文本

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
  const [error, setError] = useState<string | null>(null);

  const isStoppingRef = useRef(false);

  // 权限管理
  const { state: permissionState, request: requestPermission } = useMediaPermission();

  // 处理服务端消息
  const handleServerMessage = useCallback((message: ServerMessage) => {
    if (message.type === 'asr_result') {
      const asrMessage = message as AsrResultMessage;
      setCurrentText(asrMessage.data.text);
      if (asrMessage.data.is_final) {
        setFinalText(asrMessage.data.text);
      }
    } else if (message.type === 'asr_end') {
      const asrEndMessage = message as AsrEndMessage;
      setFinalText(asrEndMessage.data.text);
      setState('idle');
    }
  }, []);

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
    startListening,
    stopListening,
    requestPermission,
    error: actualError,
    clearError,
  };
}
