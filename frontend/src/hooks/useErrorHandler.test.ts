/**
 * useErrorHandler Hook 测试
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useErrorHandler } from './useErrorHandler';

describe('useErrorHandler', () => {
  it('should have no error initially', () => {
    const { result } = renderHook(() => useErrorHandler());
    expect(result.current.error).toBeNull();
  });

  it('should handle server error with known code', () => {
    const { result } = renderHook(() => useErrorHandler());

    act(() => {
      result.current.handleServerError({ code: 'ASR_ERROR' });
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.error!.code).toBe('ASR_ERROR');
    expect(result.current.error!.message).toBe('语音识别服务暂时不可用');
    expect(result.current.error!.retryable).toBe(true);
  });

  it('should handle server error with custom message', () => {
    const { result } = renderHook(() => useErrorHandler());

    act(() => {
      result.current.handleServerError({ code: 'LLM_ERROR', message: '自定义错误消息' });
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.error!.message).toBe('自定义错误消息');
  });

  it('should handle unknown error code', () => {
    const { result } = renderHook(() => useErrorHandler());

    act(() => {
      result.current.handleServerError({ code: 'SOME_UNKNOWN_CODE' });
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.error!.message).toBe('发生未知错误');
    expect(result.current.error!.retryable).toBe(false);
  });

  it('should clear error', () => {
    const { result } = renderHook(() => useErrorHandler());

    act(() => {
      result.current.handleServerError({ code: 'ASR_ERROR' });
    });

    expect(result.current.error).not.toBeNull();

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });

  it('should call onRetry callback when retry is called', () => {
    const onRetry = vi.fn();
    const { result } = renderHook(() => useErrorHandler(onRetry));

    act(() => {
      result.current.handleServerError({ code: 'ASR_ERROR' });
    });

    act(() => {
      result.current.retry();
    });

    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(result.current.error).toBeNull();
  });

  it('should set error directly', () => {
    const { result } = renderHook(() => useErrorHandler());

    act(() => {
      result.current.setError({
        code: 'CUSTOM_ERROR',
        message: '自定义错误',
        retryable: false,
      });
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.error!.code).toBe('CUSTOM_ERROR');
  });
});
