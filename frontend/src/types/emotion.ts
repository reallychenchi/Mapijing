export type EmotionType = 'default' | 'empathy' | 'comfort' | 'happy';

export type Speaker = 'user' | 'assistant';

export const EMOTION_MAP: Record<string, EmotionType> = {
  '默认陪伴': 'default',
  '共情倾听': 'empathy',
  '安慰支持': 'comfort',
  '轻松愉悦': 'happy',
};

// Use import.meta.env.BASE_URL to handle base path correctly in production
// For files in public/ directory, Vite doesn't process them via import
const getAvatarPath = (filename: string) => `${import.meta.env.BASE_URL}assets/avatars/${filename}`;

export const AVATAR_MAP: Record<EmotionType, string> = {
  default: getAvatarPath('default.png'),
  empathy: getAvatarPath('empathy.png'),
  comfort: getAvatarPath('comfort.png'),
  happy: getAvatarPath('happy.png'),
};
