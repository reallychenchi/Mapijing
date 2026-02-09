/**
 * 错误处理 Hook
 * 统一处理各种错误类型，提供用户友好的错误信息和重试功能
 */

import { useState, useCallback } from 'react';

export interface ErrorInfo {
  code: string;
  message: string;
  retryable: boolean;
}

const ERROR_MESSAGES: Record<string, string> = {
  ASR_ERROR: '语音识别服务暂时不可用',
  LLM_ERROR: '对话服务暂时不可用',
  TTS_ERROR: '语音合成服务暂时不可用',
  NETWORK_ERROR: '网络连接失败',
  UNKNOWN_ERROR: '发生未知错误',
};

const RETRYABLE_ERRORS = ['ASR_ERROR', 'LLM_ERROR', 'TTS_ERROR', 'NETWORK_ERROR'];

export interface UseErrorHandlerReturn {
  error: ErrorInfo | null;
  setError: (error: ErrorInfo | null) => void;
  handleServerError: (errorData: { code: string; message?: string }) => void;
  clearError: () => void;
  retry: () => void;
}

export function useErrorHandler(onRetry?: () => void): UseErrorHandlerReturn {
  const [error, setError] = useState<ErrorInfo | null>(null);

  const handleServerError = useCallback((errorData: { code: string; message?: string }) => {
    const message = errorData.message || ERROR_MESSAGES[errorData.code] || ERROR_MESSAGES.UNKNOWN_ERROR;

    setError({
      code: errorData.code,
      message,
      retryable: RETRYABLE_ERRORS.includes(errorData.code),
    });
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const retry = useCallback(() => {
    clearError();
    onRetry?.();
  }, [clearError, onRetry]);

  return {
    error,
    setError,
    handleServerError,
    clearError,
    retry,
  };
}
