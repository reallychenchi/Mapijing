import React from 'react';
import './EarIndicator.css';

export interface EarIndicatorProps {
  isBlinking: boolean;
  visible?: boolean;
}

export const EarIndicator: React.FC<EarIndicatorProps> = ({ isBlinking, visible = true }) => {
  if (!visible) {
    return null;
  }

  return (
    <span
      className={`ear-indicator ${isBlinking ? 'ear-indicator--blinking' : ''}`}
      role="img"
      aria-label="耳朵提示"
    >
      👂
    </span>
  );
};
