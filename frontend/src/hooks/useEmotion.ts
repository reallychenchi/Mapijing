import { useState, useCallback } from 'react';
import type { EmotionType } from '../types/emotion';
import { EMOTION_MAP } from '../types/emotion';

export interface UseEmotionReturn {
  emotion: EmotionType;
  setEmotion: (emotion: EmotionType) => void;
  setEmotionFromServer: (serverEmotion: string) => void;
}

export function useEmotion(initialEmotion: EmotionType = 'default'): UseEmotionReturn {
  const [emotion, setEmotionState] = useState<EmotionType>(initialEmotion);

  const setEmotion = useCallback((newEmotion: EmotionType) => {
    setEmotionState(newEmotion);
  }, []);

  const setEmotionFromServer = useCallback((serverEmotion: string) => {
    const mappedEmotion = EMOTION_MAP[serverEmotion];
    if (mappedEmotion) {
      setEmotionState(mappedEmotion);
    }
  }, []);

  return {
    emotion,
    setEmotion,
    setEmotionFromServer,
  };
}
