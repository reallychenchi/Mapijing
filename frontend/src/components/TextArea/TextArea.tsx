import React, { useEffect, useRef } from 'react';
import type { Speaker } from '../../types/emotion';
import { ErrorDisplay } from './ErrorDisplay';
import './TextArea.css';

export interface TextAreaProps {
  text: string;
  speaker: Speaker;
  isStreaming: boolean;
  error?: {
    message: string;
    onRetry: () => void;
  };
}

export const TextArea: React.FC<TextAreaProps> = ({
  text,
  speaker,
  isStreaming,
  error,
}) => {
  const textRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (textRef.current && isStreaming) {
      textRef.current.scrollTop = textRef.current.scrollHeight;
    }
  }, [text, isStreaming]);

  if (error) {
    return (
      <div className="text-area">
        <ErrorDisplay message={error.message} onRetry={error.onRetry} />
      </div>
    );
  }

  return (
    <div className="text-area" ref={textRef}>
      <p className={`text-content ${speaker}`}>
        {text}
        {isStreaming && <span className="cursor">|</span>}
      </p>
    </div>
  );
};
