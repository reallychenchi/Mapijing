import React from 'react';
import type { ConnectionState } from '../../services/websocket';
import './ConnectionStatus.css';

export interface ConnectionStatusProps {
  state: ConnectionState;
  onReconnect: () => void;
}

const STATUS_CONFIG: Record<ConnectionState, { label: string; color: string }> = {
  disconnected: { label: '未连接', color: '#999' },
  connecting: { label: '连接中...', color: '#ffc107' },
  connected: { label: '已连接', color: '#28a745' },
  error: { label: '连接错误', color: '#dc3545' },
};

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ state, onReconnect }) => {
  const config = STATUS_CONFIG[state];

  return (
    <div className="connection-status">
      <span className="status-indicator" style={{ backgroundColor: config.color }} />
      <span className="status-label">{config.label}</span>
      {(state === 'disconnected' || state === 'error') && (
        <button className="reconnect-button" onClick={onReconnect}>
          重新连接
        </button>
      )}
    </div>
  );
};
