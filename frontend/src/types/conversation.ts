/**
 * 对话相关类型定义
 */

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  emotion?: string; // 仅 assistant 消息有
}

export interface ConversationHistory {
  messages: Message[];
  currentEmotion: string;
  lastUpdated: number;
}

export interface ConversationState {
  messages: Message[];
  currentEmotion: string;
  isLoading: boolean;
}
