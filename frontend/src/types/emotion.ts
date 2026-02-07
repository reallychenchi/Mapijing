export type EmotionType = 'default' | 'empathy' | 'comfort' | 'happy';

export type Speaker = 'user' | 'assistant';

export const EMOTION_MAP: Record<string, EmotionType> = {
  '默认陪伴': 'default',
  '共情倾听': 'empathy',
  '安慰支持': 'comfort',
  '轻松愉悦': 'happy',
};

export const AVATAR_MAP: Record<EmotionType, string> = {
  default: '/assets/avatars/default.png',
  empathy: '/assets/avatars/empathy.png',
  comfort: '/assets/avatars/comfort.png',
  happy: '/assets/avatars/happy.png',
};
