/**
 * storage 服务测试
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { storage } from './storage';
import type { Message, ConversationHistory } from '../types/conversation';

describe('storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should save and load conversation', () => {
    const history: ConversationHistory = {
      messages: [{ id: '1', role: 'user' as const, content: '你好', timestamp: Date.now() }],
      currentEmotion: '默认陪伴',
      lastUpdated: Date.now(),
    };

    storage.saveConversation(history);
    const loaded = storage.loadConversation();

    expect(loaded).not.toBeNull();
    expect(loaded!.messages.length).toBe(1);
    expect(loaded!.messages[0].content).toBe('你好');
  });

  it('should return null when no conversation exists', () => {
    const loaded = storage.loadConversation();
    expect(loaded).toBeNull();
  });

  it('should clear conversation', () => {
    const history: ConversationHistory = {
      messages: [],
      currentEmotion: '默认陪伴',
      lastUpdated: Date.now(),
    };

    storage.saveConversation(history);
    storage.clearConversation();
    const loaded = storage.loadConversation();

    expect(loaded).toBeNull();
  });

  it('should add message to history', () => {
    const message: Message = {
      id: '1',
      role: 'user',
      content: '测试消息',
      timestamp: Date.now(),
    };

    storage.addMessage(message);
    const loaded = storage.loadConversation();

    expect(loaded).not.toBeNull();
    expect(loaded!.messages.length).toBe(1);
    expect(loaded!.messages[0].content).toBe('测试消息');
  });

  it('should update emotion', () => {
    const history: ConversationHistory = {
      messages: [],
      currentEmotion: '默认陪伴',
      lastUpdated: Date.now(),
    };

    storage.saveConversation(history);
    storage.updateEmotion('共情倾听');
    const loaded = storage.loadConversation();

    expect(loaded).not.toBeNull();
    expect(loaded!.currentEmotion).toBe('共情倾听');
  });

  it('should limit message count', () => {
    const messages: Message[] = [];
    for (let i = 0; i < 150; i++) {
      messages.push({
        id: `${i}`,
        role: 'user',
        content: `消息 ${i}`,
        timestamp: Date.now(),
      });
    }

    const history: ConversationHistory = {
      messages,
      currentEmotion: '默认陪伴',
      lastUpdated: Date.now(),
    };

    storage.saveConversation(history);
    const loaded = storage.loadConversation();

    expect(loaded).not.toBeNull();
    // 应该被截断到 100 条
    expect(loaded!.messages.length).toBe(100);
  });

  it('should return storage usage', () => {
    const usage = storage.getStorageUsage();
    expect(usage).toHaveProperty('used');
    expect(usage).toHaveProperty('total');
    expect(typeof usage.used).toBe('number');
    expect(usage.total).toBe(5 * 1024 * 1024);
  });
});
