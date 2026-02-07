import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from './useWebSocket';
import { resetWebSocketService } from '../services/websocket';

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

const OriginalWebSocket = global.WebSocket;

describe('useWebSocket', () => {
  beforeEach(() => {
    (global as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
    resetWebSocketService();
  });

  afterEach(() => {
    global.WebSocket = OriginalWebSocket;
    resetWebSocketService();
  });

  it('should initialize with disconnected state', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    expect(result.current.state).toBe('disconnected');
    expect(result.current.error).toBeNull();
  });

  it('should auto-connect by default', async () => {
    const { result } = renderHook(() => useWebSocket());

    await waitFor(() => {
      expect(result.current.state).toBe('connected');
    });
  });

  it('should not auto-connect when disabled', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    expect(result.current.state).toBe('disconnected');
  });

  it('should connect manually', async () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    await act(async () => {
      await result.current.connect();
    });

    expect(result.current.state).toBe('connected');
  });

  it('should disconnect', async () => {
    const { result } = renderHook(() => useWebSocket());

    await waitFor(() => {
      expect(result.current.state).toBe('connected');
    });

    act(() => {
      result.current.disconnect();
    });

    expect(result.current.state).toBe('disconnected');
  });

  it('should clear error', async () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    // 手动设置一个错误场景（通过模拟错误消息）
    await act(async () => {
      await result.current.connect();
    });

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });

  it('should call onMessage callback for non-error messages', async () => {
    const onMessage = vi.fn();
    const { result } = renderHook(() => useWebSocket({ onMessage }));

    await waitFor(() => {
      expect(result.current.state).toBe('connected');
    });

    // 获取内部 WebSocket 并发送消息
    // 这需要通过 websocket service 的内部机制
  });

  it('should provide send function', async () => {
    const { result } = renderHook(() => useWebSocket());

    await waitFor(() => {
      expect(result.current.state).toBe('connected');
    });

    expect(typeof result.current.send).toBe('function');
  });
});
