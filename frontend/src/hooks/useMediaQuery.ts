import { useSyncExternalStore } from 'react';

function getServerSnapshot(): boolean {
  return false;
}

export function useMediaQuery(maxWidth: number): boolean {
  const subscribe = (callback: () => void) => {
    const mediaQuery = window.matchMedia(`(max-width: ${maxWidth - 1}px)`);
    mediaQuery.addEventListener('change', callback);
    return () => mediaQuery.removeEventListener('change', callback);
  };

  const getSnapshot = () => {
    return window.matchMedia(`(max-width: ${maxWidth - 1}px)`).matches;
  };

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
