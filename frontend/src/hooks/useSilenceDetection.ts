/**
 * 静默检测 Hook
 * 检测用户是否静默，触发耳朵图标闪动
 *
 * 技术规格：
 * - 静默阈值：5秒无语音输入
 * - 闪动间隔：2秒闪一次
 * - 每组闪动次数：3次（共6秒）
 * - 组间间隔：10秒
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export interface SilenceConfig {
  silenceThreshold: number; // 静默阈值（毫秒）
  blinkInterval: number; // 闪动间隔（毫秒）
  blinksPerGroup: number; // 每组闪动次数
  groupInterval: number; // 组间间隔（毫秒）
}

export interface UseSilenceDetectionReturn {
  isSilent: boolean;
  shouldBlink: boolean;
  resetSilenceTimer: () => void;
}

const DEFAULT_CONFIG: SilenceConfig = {
  silenceThreshold: 5000, // 5秒
  blinkInterval: 2000, // 2秒
  blinksPerGroup: 3, // 3次
  groupInterval: 10000, // 10秒
};

export function useSilenceDetection(
  config: SilenceConfig = DEFAULT_CONFIG
): UseSilenceDetectionReturn {
  const [isSilent, setIsSilent] = useState(false);
  const [shouldBlink, setShouldBlink] = useState(false);

  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const blinkTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const blinkCountRef = useRef(0);
  const isBlinkingRef = useRef(false);

  // 停止闪动
  const stopBlinking = useCallback(() => {
    if (blinkTimerRef.current) {
      clearTimeout(blinkTimerRef.current);
      blinkTimerRef.current = null;
    }
    setShouldBlink(false);
    blinkCountRef.current = 0;
    isBlinkingRef.current = false;
  }, []);

  // 开始闪动
  const startBlinking = useCallback(() => {
    if (isBlinkingRef.current) return;
    isBlinkingRef.current = true;
    blinkCountRef.current = 0;

    const doBlink = () => {
      if (blinkCountRef.current < config.blinksPerGroup) {
        setShouldBlink(true);

        // 闪动持续时间（500ms）
        blinkTimerRef.current = setTimeout(() => {
          setShouldBlink(false);
          blinkCountRef.current++;

          // 下一次闪动
          blinkTimerRef.current = setTimeout(doBlink, config.blinkInterval - 500);
        }, 500);
      } else {
        // 一组结束，等待组间间隔后开始下一组
        blinkCountRef.current = 0;
        blinkTimerRef.current = setTimeout(doBlink, config.groupInterval);
      }
    };

    doBlink();
  }, [config.blinkInterval, config.blinksPerGroup, config.groupInterval]);

  // 重置静默计时器
  const resetSilenceTimer = useCallback(() => {
    // 停止闪动
    stopBlinking();
    setIsSilent(false);

    // 清除现有计时器
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
    }

    // 设置新的静默检测计时器
    silenceTimerRef.current = setTimeout(() => {
      setIsSilent(true);
      startBlinking();
    }, config.silenceThreshold);
  }, [config.silenceThreshold, startBlinking, stopBlinking]);

  // 初始化静默计时器
  useEffect(() => {
    // 设置静默检测计时器
    silenceTimerRef.current = setTimeout(() => {
      setIsSilent(true);
      // 开始闪动逻辑内联处理
      if (!isBlinkingRef.current) {
        isBlinkingRef.current = true;
        blinkCountRef.current = 0;

        const doBlink = () => {
          if (blinkCountRef.current < config.blinksPerGroup) {
            setShouldBlink(true);
            blinkTimerRef.current = setTimeout(() => {
              setShouldBlink(false);
              blinkCountRef.current++;
              blinkTimerRef.current = setTimeout(doBlink, config.blinkInterval - 500);
            }, 500);
          } else {
            blinkCountRef.current = 0;
            blinkTimerRef.current = setTimeout(doBlink, config.groupInterval);
          }
        };
        doBlink();
      }
    }, config.silenceThreshold);

    return () => {
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }
      if (blinkTimerRef.current) {
        clearTimeout(blinkTimerRef.current);
      }
    };
  }, [config.silenceThreshold, config.blinkInterval, config.blinksPerGroup, config.groupInterval]);

  return {
    isSilent,
    shouldBlink,
    resetSilenceTimer,
  };
}
