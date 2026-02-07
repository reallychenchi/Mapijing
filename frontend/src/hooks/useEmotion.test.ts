import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useEmotion } from './useEmotion';

describe('useEmotion', () => {
  it('should initialize with default emotion', () => {
    const { result } = renderHook(() => useEmotion());
    expect(result.current.emotion).toBe('default');
  });

  it('should initialize with provided emotion', () => {
    const { result } = renderHook(() => useEmotion('happy'));
    expect(result.current.emotion).toBe('happy');
  });

  it('should update emotion with setEmotion', () => {
    const { result } = renderHook(() => useEmotion());

    act(() => {
      result.current.setEmotion('empathy');
    });

    expect(result.current.emotion).toBe('empathy');
  });

  it('should map server emotion to emotion type', () => {
    const { result } = renderHook(() => useEmotion());

    act(() => {
      result.current.setEmotionFromServer('共情倾听');
    });

    expect(result.current.emotion).toBe('empathy');
  });

  it('should map all server emotions correctly', () => {
    const { result } = renderHook(() => useEmotion());

    const mappings = [
      { server: '默认陪伴', expected: 'default' },
      { server: '共情倾听', expected: 'empathy' },
      { server: '安慰支持', expected: 'comfort' },
      { server: '轻松愉悦', expected: 'happy' },
    ];

    for (const { server, expected } of mappings) {
      act(() => {
        result.current.setEmotionFromServer(server);
      });
      expect(result.current.emotion).toBe(expected);
    }
  });

  it('should not change emotion for unknown server emotion', () => {
    const { result } = renderHook(() => useEmotion('happy'));

    act(() => {
      result.current.setEmotionFromServer('unknown');
    });

    expect(result.current.emotion).toBe('happy');
  });
});
