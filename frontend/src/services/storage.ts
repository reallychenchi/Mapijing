/**
 * localStorage 存储封装
 * 用于保存和恢复对话历史
 */

import type { Message, ConversationHistory } from '../types/conversation';

const STORAGE_KEYS = {
  CONVERSATION_HISTORY: 'mapijing_conversation_history',
} as const;

// 最大存储条数（防止 localStorage 超限）
const MAX_HISTORY_LENGTH = 100;

export const storage = {
  /**
   * 保存对话历史
   */
  saveConversation(history: ConversationHistory): void {
    try {
      // 限制消息数量
      const trimmedMessages = history.messages.slice(-MAX_HISTORY_LENGTH);

      const data: ConversationHistory = {
        messages: trimmedMessages,
        currentEmotion: history.currentEmotion,
        lastUpdated: Date.now(),
      };

      localStorage.setItem(STORAGE_KEYS.CONVERSATION_HISTORY, JSON.stringify(data));
    } catch (error) {
      console.error('Failed to save conversation:', error);
      // localStorage 可能已满，尝试清理旧数据
      this.clearOldData();
    }
  },

  /**
   * 加载对话历史
   */
  loadConversation(): ConversationHistory | null {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.CONVERSATION_HISTORY);
      if (!data) {
        return null;
      }

      const history: ConversationHistory = JSON.parse(data);

      // 验证数据结构
      if (!Array.isArray(history.messages)) {
        return null;
      }

      return history;
    } catch (error) {
      console.error('Failed to load conversation:', error);
      return null;
    }
  },

  /**
   * 添加单条消息
   */
  addMessage(message: Message): void {
    const history = this.loadConversation() || {
      messages: [],
      currentEmotion: '默认陪伴',
      lastUpdated: Date.now(),
    };

    history.messages.push(message);
    this.saveConversation(history);
  },

  /**
   * 更新当前情感状态
   */
  updateEmotion(emotion: string): void {
    const history = this.loadConversation();
    if (history) {
      history.currentEmotion = emotion;
      this.saveConversation(history);
    }
  },

  /**
   * 清空对话历史
   */
  clearConversation(): void {
    localStorage.removeItem(STORAGE_KEYS.CONVERSATION_HISTORY);
  },

  /**
   * 清理旧数据（localStorage 空间不足时）
   */
  clearOldData(): void {
    const history = this.loadConversation();
    if (history && history.messages.length > 10) {
      // 保留最近 10 条
      history.messages = history.messages.slice(-10);
      this.saveConversation(history);
    }
  },

  /**
   * 获取存储使用情况
   */
  getStorageUsage(): { used: number; total: number } {
    let used = 0;
    for (const key in localStorage) {
      if (Object.prototype.hasOwnProperty.call(localStorage, key)) {
        used += localStorage.getItem(key)?.length || 0;
      }
    }
    // localStorage 通常限制为 5MB
    return { used, total: 5 * 1024 * 1024 };
  },
};
