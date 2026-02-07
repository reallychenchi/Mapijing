import React from 'react';
import './ErrorDisplay.css';

export interface ErrorDisplayProps {
  message: string;
  onRetry: () => void;
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ message, onRetry }) => {
  return (
    <div className="error-display">
      <p className="error-message">{message}</p>
      <button className="retry-button" onClick={onRetry}>
        重试
      </button>
    </div>
  );
};
