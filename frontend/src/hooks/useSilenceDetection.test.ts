/**
 * useSilenceDetection Hook 测试
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useSilenceDetection } from './useSilenceDetection';

describe('useSilenceDetection', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should not blink initially', () => {
    const { result } = renderHook(() => useSilenceDetection());
    expect(result.current.shouldBlink).toBe(false);
    expect(result.current.isSilent).toBe(false);
  });

  it('should detect silence after threshold', () => {
    const { result } = renderHook(() =>
      useSilenceDetection({
        silenceThreshold: 5000,
        blinkInterval: 2000,
        blinksPerGroup: 3,
        groupInterval: 10000,
      })
    );

    // 等待 5 秒
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.isSilent).toBe(true);
  });

  it('should start blinking after silence threshold', () => {
    const { result } = renderHook(() =>
      useSilenceDetection({
        silenceThreshold: 5000,
        blinkInterval: 2000,
        blinksPerGroup: 3,
        groupInterval: 10000,
      })
    );

    // 等待 5 秒进入静默状态
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    // 此时应该开始闪动
    expect(result.current.shouldBlink).toBe(true);
  });

  it('should reset on user activity', () => {
    const { result } = renderHook(() =>
      useSilenceDetection({
        silenceThreshold: 5000,
        blinkInterval: 2000,
        blinksPerGroup: 3,
        groupInterval: 10000,
      })
    );

    // 等待进入静默状态
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.isSilent).toBe(true);

    // 重置
    act(() => {
      result.current.resetSilenceTimer();
    });

    expect(result.current.isSilent).toBe(false);
    expect(result.current.shouldBlink).toBe(false);
  });

  it('should stop blinking after reset', () => {
    const { result } = renderHook(() =>
      useSilenceDetection({
        silenceThreshold: 5000,
        blinkInterval: 2000,
        blinksPerGroup: 3,
        groupInterval: 10000,
      })
    );

    // 等待进入静默状态并开始闪动
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.shouldBlink).toBe(true);

    // 用户活动，重置
    act(() => {
      result.current.resetSilenceTimer();
    });

    expect(result.current.shouldBlink).toBe(false);
  });

  it('should blink in groups', () => {
    const { result } = renderHook(() =>
      useSilenceDetection({
        silenceThreshold: 1000,
        blinkInterval: 500,
        blinksPerGroup: 2,
        groupInterval: 2000,
      })
    );

    // 等待进入静默状态
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // 第一次闪动开始
    expect(result.current.shouldBlink).toBe(true);

    // 闪动结束 (500ms)
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current.shouldBlink).toBe(false);
  });
});
