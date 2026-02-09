import { useCallback, useMemo, useEffect } from 'react';
import { Layout } from './components/Layout';
import { AvatarArea } from './components/AvatarArea';
import { TextArea } from './components/TextArea';
import { useConversation } from './hooks/useConversation';
import { useSilenceDetection } from './hooks/useSilenceDetection';
import type { Speaker } from './types/emotion';
import './styles/global.css';

function App() {
  const {
    state: conversationState,
    permissionState,
    currentText,
    finalText,
    assistantText,
    emotion,
    isPlaying,
    startListening,
    stopListening,
    requestPermission,
    interrupt,
    error,
    clearError,
  } = useConversation();

  // 静默检测
  const { shouldBlink, resetSilenceTimer } = useSilenceDetection();

  // 用户活动时重置静默计时器
  useEffect(() => {
    if (conversationState === 'listening') {
      resetSilenceTimer();
    }
  }, [conversationState, resetSilenceTimer]);

  // 根据会话状态更新显示文本
  const displayText = useMemo(() => {
    if (conversationState === 'speaking' || conversationState === 'processing') {
      // AI 回复时显示助手文本
      return assistantText || '';
    }
    if (conversationState === 'listening') {
      // 用户说话时显示识别文本
      return currentText || '';
    }
    // idle 状态
    if (assistantText) {
      return assistantText;
    }
    if (finalText) {
      return finalText;
    }
    return '欢迎来到小马聊天，点击小马耳朵开始说话...';
  }, [conversationState, currentText, finalText, assistantText]);

  const isStreaming = conversationState === 'listening' || conversationState === 'processing' || conversationState === 'speaking';

  // 判断是否显示耳朵图标闪动
  // 只在用户静默且 AI 没有说话时显示闪动
  const showEarIndicator = true;
  const isEarBlinking = useMemo(() => {
    // 如果用户正在录音，不闪动
    if (conversationState === 'listening') {
      return false;
    }
    // 如果 AI 正在说话，不闪动
    if (isPlaying || conversationState === 'speaking') {
      return false;
    }
    // 用户静默时闪动
    return shouldBlink;
  }, [conversationState, isPlaying, shouldBlink]);

  // 录音时 speaker 为 user，否则为 assistant
  const speaker: Speaker = useMemo(
    () => (conversationState === 'listening' ? 'user' : 'assistant'),
    [conversationState]
  );

  // 处理点击小马开始/停止录音
  const handleAvatarClick = useCallback(async () => {
    // 如果 AI 正在说话，点击触发打断
    if (conversationState === 'speaking' || isPlaying) {
      interrupt();
      return;
    }

    if (permissionState !== 'granted') {
      const granted = await requestPermission();
      if (!granted) return;
    }

    if (conversationState === 'idle') {
      await startListening();
    } else if (conversationState === 'listening') {
      stopListening();
    }
  }, [conversationState, isPlaying, permissionState, requestPermission, startListening, stopListening, interrupt]);

  // 错误处理
  const errorDisplay = error
    ? {
        message: error,
        onRetry: () => {
          clearError();
        },
      }
    : undefined;

  return (
    <Layout
      avatarArea={
        <AvatarArea
          emotion={emotion}
          showEarIndicator={showEarIndicator}
          isEarBlinking={isEarBlinking}
          onClick={handleAvatarClick}
        />
      }
      textArea={
        <TextArea text={displayText} speaker={speaker} isStreaming={isStreaming} error={errorDisplay} />
      }
    />
  );
}

export default App;
