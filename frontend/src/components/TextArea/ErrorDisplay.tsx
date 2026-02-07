import React from 'react';
import type { ErrorCode } from '../../types/message';
import './ErrorDisplay.css';

export interface ErrorDisplayProps {
  message: string;
  onRetry: () => void;
  code?: ErrorCode;
}

const ERROR_LABELS: Record<ErrorCode, string> = {
  ASR_ERROR: '语音识别错误',
  LLM_ERROR: '对话服务错误',
  TTS_ERROR: '语音合成错误',
  NETWORK_ERROR: '网络连接错误',
  UNKNOWN_ERROR: '未知错误',
};

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ message, onRetry, code }) => {
  const errorTitle = code ? ERROR_LABELS[code] : '错误';

  return (
    <div className="error-display">
      <div className="error-icon">&#9888;</div>
      <div className="error-title">{errorTitle}</div>
      <div className="error-message">{message}</div>
      <button className="retry-button" onClick={onRetry}>
        点击重试
      </button>
    </div>
  );
};
