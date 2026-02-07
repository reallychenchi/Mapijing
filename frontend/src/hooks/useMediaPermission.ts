/**
 * 麦克风权限管理 Hook
 */

import { useState, useCallback } from 'react';

export type PermissionState = 'prompt' | 'granted' | 'denied' | 'checking';

export interface UseMediaPermissionReturn {
  state: PermissionState;
  request: () => Promise<boolean>;
  error: string | null;
}

export function useMediaPermission(): UseMediaPermissionReturn {
  const [state, setState] = useState<PermissionState>('prompt');
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(async (): Promise<boolean> => {
    setState('checking');
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // 立即释放，仅用于权限检查
      stream.getTracks().forEach((track) => track.stop());
      setState('granted');
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : '麦克风权限获取失败';
      setError(message);
      setState('denied');
      return false;
    }
  }, []);

  return { state, request, error };
}
