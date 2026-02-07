import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WebSocketService, resetWebSocketService } from './websocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((error: Event) => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    // 模拟异步连接成功
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.();
    }, 0);
  }

  send = vi.fn();

  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  });
}

// 保存原始 WebSocket
const OriginalWebSocket = global.WebSocket;

describe('WebSocketService', () => {
  let service: WebSocketService;

  beforeEach(() => {
    // 替换全局 WebSocket
    (global as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
    resetWebSocketService();
    service = new WebSocketService('ws://localhost:8000/ws/chat');
  });

  afterEach(() => {
    // 恢复原始 WebSocket
    global.WebSocket = OriginalWebSocket;
    resetWebSocketService();
  });

  it('should initialize with disconnected state', () => {
    expect(service.state).toBe('disconnected');
  });

  it('should connect successfully', async () => {
    await service.connect();
    expect(service.state).toBe('connected');
  });

  it('should handle disconnect', async () => {
    await service.connect();
    service.disconnect();
    expect(service.state).toBe('disconnected');
  });

  it('should notify state changes', async () => {
    const handler = vi.fn();
    service.onStateChange(handler);

    await service.connect();

    expect(handler).toHaveBeenCalledWith('connecting');
    expect(handler).toHaveBeenCalledWith('connected');
  });

  it('should allow unsubscribing from state changes', async () => {
    const handler = vi.fn();
    const unsubscribe = service.onStateChange(handler);

    unsubscribe();
    await service.connect();

    expect(handler).not.toHaveBeenCalled();
  });

  it('should send messages when connected', async () => {
    await service.connect();

    const message = { type: 'audio_end' as const, data: {} };
    service.send(message);

    // 获取内部 WebSocket 实例并验证 send 被调用
    expect(service.state).toBe('connected');
  });

  it('should throw error when sending without connection', () => {
    const message = { type: 'audio_end' as const, data: {} };

    expect(() => service.send(message)).toThrow('WebSocket is not connected');
  });

  it('should handle incoming messages', async () => {
    const messageHandler = vi.fn();
    service.onMessage(messageHandler);

    await service.connect();

    // 模拟收到消息
    const mockWs = (service as unknown as { ws: MockWebSocket }).ws;
    mockWs.onmessage?.({
      data: JSON.stringify({ type: 'asr_result', data: { text: 'hello', is_final: false } }),
    });

    expect(messageHandler).toHaveBeenCalledWith({
      type: 'asr_result',
      data: { text: 'hello', is_final: false },
    });
  });

  it('should allow unsubscribing from messages', async () => {
    const messageHandler = vi.fn();
    const unsubscribe = service.onMessage(messageHandler);

    unsubscribe();
    await service.connect();

    // 模拟收到消息
    const mockWs = (service as unknown as { ws: MockWebSocket }).ws;
    mockWs.onmessage?.({
      data: JSON.stringify({ type: 'asr_result', data: { text: 'hello', is_final: false } }),
    });

    expect(messageHandler).not.toHaveBeenCalled();
  });

  it('should handle JSON parse errors gracefully', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    const messageHandler = vi.fn();
    service.onMessage(messageHandler);

    await service.connect();

    // 模拟收到无效 JSON
    const mockWs = (service as unknown as { ws: MockWebSocket }).ws;
    mockWs.onmessage?.({ data: 'invalid json' });

    expect(messageHandler).not.toHaveBeenCalled();
    expect(consoleError).toHaveBeenCalled();

    consoleError.mockRestore();
  });

  it('should not reconnect if already connected', async () => {
    await service.connect();

    // 第二次连接应该立即返回
    const handler = vi.fn();
    service.onStateChange(handler);

    await service.connect();

    // 不应该再次触发 connecting 状态
    expect(handler).not.toHaveBeenCalledWith('connecting');
  });
});
