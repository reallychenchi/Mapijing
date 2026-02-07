import { useCallback, useMemo } from 'react';
import { Layout } from './components/Layout';
import { AvatarArea } from './components/AvatarArea';
import { TextArea } from './components/TextArea';
import { useEmotion } from './hooks/useEmotion';
import { useConversation } from './hooks/useConversation';
import type { Speaker } from './types/emotion';
import './styles/global.css';

function App() {
  const { emotion } = useEmotion('default');

  const {
    state: conversationState,
    permissionState,
    currentText,
    finalText,
    startListening,
    stopListening,
    requestPermission,
    error,
    clearError,
  } = useConversation();

  // 根据会话状态更新显示
  const displayText =
    conversationState === 'idle' && !currentText && !finalText
      ? '欢迎来到小马聊天，点击小马耳朵开始说话...'
      : currentText || finalText || '';

  const isStreaming = conversationState === 'listening' || conversationState === 'processing';
  const showEarIndicator = true;
  const isEarBlinking = conversationState === 'listening';

  // 录音时 speaker 为 user，否则为 assistant
  const speaker: Speaker = useMemo(
    () => (conversationState === 'listening' ? 'user' : 'assistant'),
    [conversationState]
  );

  // 处理点击小马开始/停止录音
  const handleAvatarClick = useCallback(async () => {
    if (permissionState !== 'granted') {
      const granted = await requestPermission();
      if (!granted) return;
    }

    if (conversationState === 'idle') {
      await startListening();
    } else if (conversationState === 'listening') {
      stopListening();
    }
  }, [conversationState, permissionState, requestPermission, startListening, stopListening]);

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
