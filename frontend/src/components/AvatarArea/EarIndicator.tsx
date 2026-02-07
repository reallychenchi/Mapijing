import React from 'react';
import './EarIndicator.css';

export interface EarIndicatorProps {
  isBlinking: boolean;
}

export const EarIndicator: React.FC<EarIndicatorProps> = ({ isBlinking }) => {
  return (
    <span
      className={`ear-indicator ${isBlinking ? 'blinking' : ''}`}
      role="img"
      aria-label="耳朵提示"
    >
      👂
    </span>
  );
};
