import { useState } from 'react';
import { Layout } from './components/Layout';
import { AvatarArea } from './components/AvatarArea';
import { TextArea } from './components/TextArea';
import { useEmotion } from './hooks/useEmotion';
import type { Speaker } from './types/emotion';
import './styles/global.css';

function App() {
  const { emotion } = useEmotion('default');
  const [text, setText] = useState<string>('欢迎来到小马聊天，请开始说话...');
  const [speaker, setSpeaker] = useState<Speaker>('assistant');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [showEarIndicator, setShowEarIndicator] = useState<boolean>(true);
  const [isEarBlinking, setIsEarBlinking] = useState<boolean>(true);
  const [error, setError] = useState<{ message: string; onRetry: () => void } | undefined>(undefined);

  // These will be used in future phases
  void setText;
  void setSpeaker;
  void setIsStreaming;
  void setShowEarIndicator;
  void setIsEarBlinking;
  void setError;

  return (
    <Layout
      avatarArea={
        <AvatarArea
          emotion={emotion}
          showEarIndicator={showEarIndicator}
          isEarBlinking={isEarBlinking}
        />
      }
      textArea={
        <TextArea
          text={text}
          speaker={speaker}
          isStreaming={isStreaming}
          error={error}
        />
      }
    />
  );
}

export default App;
