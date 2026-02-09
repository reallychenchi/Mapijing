/**
 * 音频播放队列 Hook
 * 管理 TTS 音频片段的播放队列，确保按顺序播放
 */

import { useRef, useState, useCallback } from 'react';

interface AudioChunk {
  audio: string; // Base64 encoded MP3
  seq: number;
}

interface UseAudioPlayerReturn {
  isPlaying: boolean;
  currentSeq: number;
  enqueue: (chunk: AudioChunk) => void;
  stop: () => void;
  clear: () => void;
}

export function useAudioPlayer(): UseAudioPlayerReturn {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentSeq, setCurrentSeq] = useState(0);

  const queueRef = useRef<AudioChunk[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const isProcessingRef = useRef(false);
  const shouldStopRef = useRef(false);
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);

  // 获取或创建 AudioContext
  const getAudioContext = useCallback((): AudioContext => {
    if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
      audioContextRef.current = new AudioContext();
    }
    // 恢复 suspended 状态的 AudioContext
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
    return audioContextRef.current;
  }, []);

  // Base64 转 ArrayBuffer
  const base64ToArrayBuffer = useCallback((base64: string): ArrayBuffer => {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }, []);

  // 播放单个音频
  const playAudio = useCallback(
    async (chunk: AudioChunk): Promise<void> => {
      if (!chunk.audio) {
        // 空音频，直接跳过
        return;
      }

      const audioContext = getAudioContext();

      try {
        // 解码音频
        const arrayBuffer = base64ToArrayBuffer(chunk.audio);
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0));

        // 创建播放源
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        currentSourceRef.current = source;

        // 等待播放完成
        return new Promise((resolve) => {
          source.onended = () => {
            currentSourceRef.current = null;
            resolve();
          };
          source.start();
          setCurrentSeq(chunk.seq);
        });
      } catch (error) {
        console.error('Audio decode/playback error:', error);
        // 解码失败，继续处理下一个
      }
    },
    [getAudioContext, base64ToArrayBuffer]
  );

  // 处理队列
  const processQueue = useCallback(async () => {
    if (isProcessingRef.current) return;

    isProcessingRef.current = true;
    setIsPlaying(true);

    while (queueRef.current.length > 0 && !shouldStopRef.current) {
      // 按 seq 排序，取出最小的
      queueRef.current.sort((a, b) => a.seq - b.seq);
      const chunk = queueRef.current.shift()!;

      try {
        await playAudio(chunk);
      } catch (error) {
        console.error('Audio playback error:', error);
      }
    }

    isProcessingRef.current = false;
    setIsPlaying(false);
    shouldStopRef.current = false;
  }, [playAudio]);

  // 入队
  const enqueue = useCallback(
    (chunk: AudioChunk) => {
      if (!chunk.audio) {
        // 空音频不入队
        return;
      }

      queueRef.current.push(chunk);

      // 开始处理（如果还没有在处理）
      if (!isProcessingRef.current) {
        processQueue();
      }
    },
    [processQueue]
  );

  // 停止播放
  const stop = useCallback(() => {
    shouldStopRef.current = true;

    // 停止当前播放的音频
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch {
        // 忽略已经停止的错误
      }
      currentSourceRef.current = null;
    }
  }, []);

  // 清空队列并停止
  const clear = useCallback(() => {
    queueRef.current = [];
    stop();
    setCurrentSeq(0);
  }, [stop]);

  return {
    isPlaying,
    currentSeq,
    enqueue,
    stop,
    clear,
  };
}
