/**
 * WebSocket 服务
 */

import type { ClientMessage, ServerMessage } from '../types/message';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export type MessageHandler = (message: ServerMessage) => void;
export type StateChangeHandler = (state: ConnectionState) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private messageHandlers: Set<MessageHandler> = new Set();
  private stateChangeHandlers: Set<StateChangeHandler> = new Set();
  private _state: ConnectionState = 'disconnected';

  constructor(url: string) {
    this.url = url;
  }

  get state(): ConnectionState {
    return this._state;
  }

  private setState(state: ConnectionState): void {
    this._state = state;
    this.stateChangeHandlers.forEach((handler) => handler(state));
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      this.setState('connecting');
      this.ws = new WebSocket(this.url);

      this.ws.onopen = (): void => {
        this.setState('connected');
        resolve();
      };

      this.ws.onclose = (): void => {
        this.setState('disconnected');
      };

      this.ws.onerror = (error): void => {
        this.setState('error');
        reject(error);
      };

      this.ws.onmessage = (event): void => {
        try {
          const message: ServerMessage = JSON.parse(event.data);
          this.messageHandlers.forEach((handler) => handler(message));
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setState('disconnected');
  }

  send(message: ClientMessage): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }
    this.ws.send(JSON.stringify(message));
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStateChange(handler: StateChangeHandler): () => void {
    this.stateChangeHandlers.add(handler);
    return () => this.stateChangeHandlers.delete(handler);
  }
}

// 单例
let wsService: WebSocketService | null = null;

export function getWebSocketService(): WebSocketService {
  if (!wsService) {
    const wsUrl = `ws://${window.location.hostname}:8000/ws/chat`;
    wsService = new WebSocketService(wsUrl);
  }
  return wsService;
}

// 用于测试的重置函数
export function resetWebSocketService(): void {
  if (wsService) {
    wsService.disconnect();
    wsService = null;
  }
}
