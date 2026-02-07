/**
 * WebSocket 连接管理 Hook
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { ConnectionState } from '../services/websocket';
import { getWebSocketService, WebSocketService } from '../services/websocket';
import type { ClientMessage, ServerMessage, ErrorMessage } from '../types/message';

export interface UseWebSocketOptions {
  autoConnect?: boolean;
  onMessage?: (message: ServerMessage) => void;
  onError?: (error: ErrorMessage) => void;
}

export interface UseWebSocketReturn {
  state: ConnectionState;
  connect: () => Promise<void>;
  disconnect: () => void;
  send: (message: ClientMessage) => void;
  error: ErrorMessage | null;
  clearError: () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { autoConnect = true, onMessage, onError } = options;

  const [state, setState] = useState<ConnectionState>('disconnected');
  const [error, setError] = useState<ErrorMessage | null>(null);
  const wsRef = useRef<WebSocketService | null>(null);

  // 使用 ref 保存回调以避免重新订阅
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onErrorRef.current = onError;
  }, [onMessage, onError]);

  useEffect(() => {
    wsRef.current = getWebSocketService();

    // 订阅状态变化
    const unsubState = wsRef.current.onStateChange(setState);

    // 订阅消息
    const unsubMessage = wsRef.current.onMessage((message) => {
      if (message.type === 'error') {
        setError(message as ErrorMessage);
        onErrorRef.current?.(message as ErrorMessage);
      } else {
        onMessageRef.current?.(message);
      }
    });

    // 自动连接
    if (autoConnect) {
      wsRef.current.connect().catch(console.error);
    }

    return () => {
      unsubState();
      unsubMessage();
    };
  }, [autoConnect]);

  const connect = useCallback(async () => {
    setError(null);
    await wsRef.current?.connect();
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
  }, []);

  const send = useCallback((message: ClientMessage) => {
    wsRef.current?.send(message);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    state,
    connect,
    disconnect,
    send,
    error,
    clearError,
  };
}
