import { useState, useCallback, useRef, useEffect } from 'react';
import './E2ETest.css';

// WebSocket 消息类型
interface WSMessage {
  type: string;
  data: Record<string, unknown>;
  timestamp?: number;
}

// 会话状态
type SessionState = 'disconnected' | 'connecting' | 'connected' | 'listening' | 'processing' | 'speaking';

// 对话消息
interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: number;
}

export function E2ETest() {
  // WebSocket 和会话状态
  const [sessionState, setSessionState] = useState<SessionState>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // 对话内容
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentText, setCurrentText] = useState(''); // 当前识别/回复的文本
  const [inputText, setInputText] = useState(''); // 文本输入框内容

  // 录音相关
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const isRecordingRef = useRef(false);

  // 音频播放
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const playbackContextRef = useRef<AudioContext | null>(null);

  // 清理函数
  const cleanup = useCallback(() => {
    // 停止录音
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    isRecordingRef.current = false;

    // 清理播放
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    if (playbackContextRef.current) {
      playbackContextRef.current.close();
      playbackContextRef.current = null;
    }

    // 关闭 WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // 组件卸载时清理
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  // Base64 解码为 ArrayBuffer
  const base64ToArrayBuffer = (base64: string): ArrayBuffer => {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  };

  // 播放音频队列
  const playAudioQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) {
      return;
    }

    isPlayingRef.current = true;

    while (audioQueueRef.current.length > 0) {
      const audioData = audioQueueRef.current.shift();
      if (!audioData) continue;

      try {
        if (!playbackContextRef.current) {
          playbackContextRef.current = new AudioContext({ sampleRate: 24000 });
        }

        // PCM 数据转换为 AudioBuffer (24kHz, 32bit float, mono)
        const pcmData = new Float32Array(audioData);
        const audioBuffer = playbackContextRef.current.createBuffer(1, pcmData.length, 24000);
        audioBuffer.getChannelData(0).set(pcmData);

        const source = playbackContextRef.current.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(playbackContextRef.current.destination);

        await new Promise<void>((resolve) => {
          source.onended = () => resolve();
          source.start();
        });
      } catch (e) {
        console.error('播放音频失败:', e);
      }
    }

    isPlayingRef.current = false;
  }, []);

  // 处理 WebSocket 消息
  const handleWSMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WSMessage = JSON.parse(event.data);
      console.log('收到消息:', message.type, message.data);

      switch (message.type) {
        case 'session_started':
          setSessionState('connected');
          setError(null);
          break;

        case 'asr_result': {
          const { text, is_final } = message.data as { text: string; is_final: boolean };
          setCurrentText(text);
          if (is_final) {
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              role: 'user',
              text,
              timestamp: Date.now(),
            }]);
            setCurrentText('');
          }
          break;
        }

        case 'asr_end':
          setSessionState('processing');
          break;

        case 'chat_text': {
          const { text } = message.data as { text: string };
          setCurrentText(prev => prev + text);
          setSessionState('speaking');
          break;
        }

        case 'tts_chunk': {
          const { audio } = message.data as { audio: string };
          if (audio) {
            const audioBuffer = base64ToArrayBuffer(audio);
            audioQueueRef.current.push(audioBuffer);
            playAudioQueue();
          }
          break;
        }

        case 'tts_end': {
          const { full_text } = message.data as { full_text: string };
          if (full_text || currentText) {
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              role: 'assistant',
              text: full_text || currentText,
              timestamp: Date.now(),
            }]);
          }
          setCurrentText('');
          setSessionState('connected');
          break;
        }

        case 'error': {
          const { message: errorMsg } = message.data as { message: string };
          setError(errorMsg);
          console.error('服务端错误:', errorMsg);
          break;
        }

        default:
          console.log('未处理的消息类型:', message.type);
      }
    } catch (e) {
      console.error('解析消息失败:', e);
    }
  }, [currentText, playAudioQueue]);

  // 连接 WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setSessionState('connecting');
    setError(null);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/e2e-chat`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket 已连接');
      // 启动会话
      ws.send(JSON.stringify({
        type: 'start_session',
        data: { input_mod: 'audio' }
      }));
    };

    ws.onmessage = handleWSMessage;

    ws.onerror = (e) => {
      console.error('WebSocket 错误:', e);
      setError('WebSocket 连接错误');
      setSessionState('disconnected');
    };

    ws.onclose = () => {
      console.log('WebSocket 已关闭');
      setSessionState('disconnected');
      wsRef.current = null;
    };
  }, [handleWSMessage]);

  // 断开连接
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'finish_session', data: {} }));
      setTimeout(() => {
        cleanup();
        setSessionState('disconnected');
      }, 100);
    }
  }, [cleanup]);

  // 开始录音
  const startRecording = useCallback(async () => {
    if (!wsRef.current || sessionState !== 'connected') {
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });
      mediaStreamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!isRecordingRef.current || !wsRef.current) return;

        const inputData = e.inputBuffer.getChannelData(0);
        // 转换为 16bit PCM
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        // 转换为 Base64
        const bytes = new Uint8Array(pcmData.buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        const base64 = btoa(binary);

        // 发送音频数据
        wsRef.current.send(JSON.stringify({
          type: 'audio_data',
          data: { audio: base64 }
        }));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      isRecordingRef.current = true;
      setSessionState('listening');
      setCurrentText('');

    } catch (e) {
      console.error('启动录音失败:', e);
      setError('无法访问麦克风');
    }
  }, [sessionState]);

  // 停止录音
  const stopRecording = useCallback(() => {
    isRecordingRef.current = false;

    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    setSessionState('processing');
  }, []);

  // 发送文本
  const sendText = useCallback(() => {
    if (!wsRef.current || !inputText.trim() || sessionState !== 'connected') {
      return;
    }

    const text = inputText.trim();
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      text,
      timestamp: Date.now(),
    }]);
    setInputText('');

    wsRef.current.send(JSON.stringify({
      type: 'text_query',
      data: { text }
    }));

    setSessionState('processing');
  }, [inputText, sessionState]);

  // 打断
  const interrupt = useCallback(() => {
    if (wsRef.current && (sessionState === 'speaking' || sessionState === 'processing')) {
      wsRef.current.send(JSON.stringify({ type: 'interrupt', data: {} }));
      audioQueueRef.current = [];
      setSessionState('connected');
      setCurrentText('');
    }
  }, [sessionState]);

  // 获取状态显示文本
  const getStatusText = () => {
    switch (sessionState) {
      case 'disconnected': return '未连接';
      case 'connecting': return '连接中...';
      case 'connected': return '已连接';
      case 'listening': return '正在听...';
      case 'processing': return '处理中...';
      case 'speaking': return 'AI 说话中...';
      default: return sessionState;
    }
  };

  return (
    <div className="e2e-test-container">
      <h1>端到端语音对话测试</h1>

      {/* 状态和控制区 */}
      <div className="control-panel">
        <div className="status">
          <span className={`status-dot ${sessionState}`}></span>
          <span>{getStatusText()}</span>
        </div>

        <div className="buttons">
          {sessionState === 'disconnected' ? (
            <button onClick={connect} className="btn primary">
              连接
            </button>
          ) : (
            <button onClick={disconnect} className="btn danger">
              断开
            </button>
          )}

          {sessionState === 'connected' && (
            <button
              onMouseDown={startRecording}
              onMouseUp={stopRecording}
              onMouseLeave={stopRecording}
              className="btn record"
            >
              按住说话
            </button>
          )}

          {sessionState === 'listening' && (
            <button onClick={stopRecording} className="btn recording">
              松开结束
            </button>
          )}

          {(sessionState === 'speaking' || sessionState === 'processing') && (
            <button onClick={interrupt} className="btn warning">
              打断
            </button>
          )}
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>关闭</button>
        </div>
      )}

      {/* 对话区域 */}
      <div className="chat-area">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="message-role">{msg.role === 'user' ? '你' : 'AI'}</div>
            <div className="message-text">{msg.text}</div>
          </div>
        ))}

        {/* 当前正在输入/回复的文本 */}
        {currentText && (
          <div className={`message ${sessionState === 'listening' ? 'user' : 'assistant'} current`}>
            <div className="message-role">
              {sessionState === 'listening' ? '你' : 'AI'}
            </div>
            <div className="message-text">{currentText}</div>
          </div>
        )}
      </div>

      {/* 文本输入区 */}
      <div className="input-area">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendText()}
          placeholder="输入文本消息..."
          disabled={sessionState !== 'connected'}
        />
        <button
          onClick={sendText}
          disabled={sessionState !== 'connected' || !inputText.trim()}
          className="btn primary"
        >
          发送
        </button>
      </div>
    </div>
  );
}

export default E2ETest;
