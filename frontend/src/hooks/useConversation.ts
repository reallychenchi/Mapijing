/**
 * 会话管理 Hook
 * 整合录音、WebSocket、ASR 结果处理、TTS 音频播放
 */

import { useState, useCallback, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAudioRecorder } from './useAudioRecorder';
import { useMediaPermission } from './useMediaPermission';
import { useEmotion } from './useEmotion';
import { useAudioPlayer } from './useAudioPlayer';
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

  // 操作
  startListening: () => Promise<void>;
  stopListening: () => void;
  requestPermission: () => Promise<boolean>;
  interrupt: () => void;

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

  const isStoppingRef = useRef(false);

  // 权限管理
  const { state: permissionState, request: requestPermission } = useMediaPermission();

  // 情感状态管理
  const { emotion, setEmotionFromServer } = useEmotion();

  // 音频播放管理
  const { enqueue, clear: clearAudio, isPlaying } = useAudioPlayer();

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
        // 不立即切换到 idle，等待 TTS 回复
        setState('processing');
      } else if (message.type === 'emotion') {
        const emotionMessage = message as EmotionMessage;
        setEmotionFromServer(emotionMessage.data.emotion);
      } else if (message.type === 'llm_response') {
        // 阶段4兼容：非流式 LLM 响应
        const llmMessage = message as LlmResponseMessage;
        setAssistantText(llmMessage.data.text);
        setSpeaker('assistant');
        setIsStreaming(false);
        setState('idle');
      } else if (message.type === 'tts_chunk') {
        // 阶段5：TTS 文字+音频片段
        const ttsMessage = message as TtsChunkMessage;
        if (ttsMessage.data.seq === 1) {
          // 第一个片段，清空之前的文字
          setAssistantText(ttsMessage.data.text);
        } else {
          // 追加文字
          setAssistantText((prev) => prev + ttsMessage.data.text);
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
        if (ttsEndMessage.data.full_text) {
          // 更新为完整文本
          setAssistantText(ttsEndMessage.data.full_text);
        }
        setIsStreaming(false);
        setState('idle');
      }
    },
    [setEmotionFromServer, enqueue]
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
    startListening,
    stopListening,
    requestPermission,
    interrupt,
    error: actualError,
    clearError,
  };
}
