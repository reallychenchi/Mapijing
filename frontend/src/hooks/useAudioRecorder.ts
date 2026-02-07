/**
 * 录音管理 Hook
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { processAudioData } from '../services/audioProcessor';

export type RecordingState = 'idle' | 'recording' | 'stopping';

export interface UseAudioRecorderOptions {
  onAudioData: (base64Audio: string, seq: number) => void;
  onError: (error: string) => void;
}

export interface UseAudioRecorderReturn {
  state: RecordingState;
  start: () => Promise<void>;
  stop: () => void;
}

export function useAudioRecorder(options: UseAudioRecorderOptions): UseAudioRecorderReturn {
  const { onAudioData, onError } = options;

  const [state, setState] = useState<RecordingState>('idle');
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const seqRef = useRef<number>(0);

  // 使用 ref 保存回调以避免依赖变化导致的问题
  const onAudioDataRef = useRef(onAudioData);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onAudioDataRef.current = onAudioData;
    onErrorRef.current = onError;
  }, [onAudioData, onError]);

  const start = useCallback(async () => {
    try {
      setState('recording');
      seqRef.current = 0;

      // 获取麦克风流
      mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000, // 请求 16kHz，浏览器可能不支持
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      // 创建 AudioContext
      audioContextRef.current = new AudioContext();
      const source = audioContextRef.current.createMediaStreamSource(mediaStreamRef.current);
      const sampleRate = audioContextRef.current.sampleRate;

      // 创建 ScriptProcessorNode（4096 样本 ≈ 85ms @ 48kHz）
      processorRef.current = audioContextRef.current.createScriptProcessor(4096, 1, 1);

      processorRef.current.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        const base64Audio = processAudioData(inputData, sampleRate);
        seqRef.current += 1;
        onAudioDataRef.current(base64Audio, seqRef.current);
      };

      // 连接节点
      source.connect(processorRef.current);
      processorRef.current.connect(audioContextRef.current.destination);
    } catch (err) {
      const message = err instanceof Error ? err.message : '录音启动失败';
      onErrorRef.current(message);
      setState('idle');
    }
  }, []);

  const stop = useCallback(() => {
    setState('stopping');

    // 断开处理器
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // 关闭 AudioContext
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // 停止媒体流
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    setState('idle');
  }, []);

  return { state, start, stop };
}
