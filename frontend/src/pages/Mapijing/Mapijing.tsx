import { useState, useCallback, useRef, useEffect } from 'react';
import './Mapijing.css';

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

export function Mapijing() {
  // WebSocket 和会话状态
  const [sessionState, setSessionState] = useState<SessionState>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // 对话内容
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentText, setCurrentText] = useState('');
  const currentTextRef = useRef(''); // 同步镜像，避免在异步回调中读取过期值
  const [currentTextRole, setCurrentTextRole] = useState<'user' | 'assistant'>('user');
  const [inputText, setInputText] = useState('');
  const msgIdCounter = useRef(0);

  // 录音相关
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const isRecordingRef = useRef(false);

  // 音频播放
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const playbackContextRef = useRef<AudioContext | null>(null);

  // 对话区域自动滚动
  const chatAreaRef = useRef<HTMLDivElement | null>(null);

  // 同步更新 currentText state 和 ref
  const setCurrentTextSync = useCallback((text: string) => {
    currentTextRef.current = text;
    setCurrentText(text);
  }, []);

  // 生成唯一消息 ID
  const newMsgId = useCallback(() => {
    msgIdCounter.current += 1;
    return `msg-${Date.now()}-${msgIdCounter.current}`;
  }, []);

  // 清理函数
  const cleanup = useCallback(() => {
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

    audioQueueRef.current = [];
    isPlayingRef.current = false;
    if (playbackContextRef.current) {
      playbackContextRef.current.close();
      playbackContextRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  // 消息更新时自动滚动到底部
  useEffect(() => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  }, [messages, currentText]);

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

      switch (message.type) {
        case 'session_started':
          setSessionState('connected');
          setError(null);
          break;

        case 'asr_result': {
          const { text, is_final } = message.data as { text: string; is_final: boolean };
          // 始终更新气泡（role 由 currentTextRole 决定，已在 startRecording 设为 'user'）
          setCurrentTextSync(text);
          if (is_final) {
            setMessages(prev => [...prev, {
              id: newMsgId(),
              role: 'user',
              text,
              timestamp: Date.now(),
            }]);
            setCurrentTextSync('');
          }
          break;
        }

        case 'asr_end':
          setSessionState('processing');
          break;

        case 'chat_text': {
          const { text } = message.data as { text: string };
          // AI 开始回复，切换气泡角色为 assistant
          setCurrentTextRole('assistant');
          const updated = currentTextRef.current + text;
          setCurrentTextSync(updated);
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
          // 用 ref 读取当前文本，避免嵌套 setter（StrictMode 下会双重触发）
          const finalText = full_text || currentTextRef.current;
          if (finalText) {
            setMessages(prev => [...prev, {
              id: newMsgId(),
              role: 'assistant',
              text: finalText,
              timestamp: Date.now(),
            }]);
          }
          setCurrentTextSync('');
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
  }, [playAudioQueue, setCurrentTextSync, newMsgId]);

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
      ws.send(JSON.stringify({
        type: 'start_session',
        data: { input_mod: 'audio' }
      }));
    };

    ws.onmessage = handleWSMessage;

    ws.onerror = () => {
      setError('连接失败，请检查网络或服务是否正常');
      setSessionState('disconnected');
    };

    ws.onclose = () => {
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
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        const bytes = new Uint8Array(pcmData.buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        const base64 = btoa(binary);

        wsRef.current.send(JSON.stringify({
          type: 'audio_data',
          data: { audio: base64 }
        }));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      isRecordingRef.current = true;
      setCurrentTextRole('user');
      setCurrentTextSync('');
      setSessionState('listening');

    } catch (e) {
      console.error('启动录音失败:', e);
      setError('无法访问麦克风，请检查权限设置');
    }
  }, [sessionState, setCurrentTextSync]);

  // 停止录音
  const stopRecording = useCallback(() => {
    if (!isRecordingRef.current) return;

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
      setCurrentTextSync('');
    }
  }, [sessionState, setCurrentTextSync]);

  const isBusy = sessionState === 'processing' || sessionState === 'speaking';
  const isConnected = sessionState !== 'disconnected' && sessionState !== 'connecting';

  // ===== 未连接状态 =====
  if (!isConnected) {
    return (
      <div className="mpj-landing">
        <h1 className="mpj-title">马屁精来喽！</h1>
        <div className="mpj-landing-body">
          <img
            src="/assets/avatars/default.png"
            alt="马屁精"
            className="mpj-avatar"
          />
          <button
            onClick={connect}
            disabled={sessionState === 'connecting'}
            className="mpj-connect-btn"
          >
            {sessionState === 'connecting' ? '连接中...' : '连接'}
          </button>
          {error && (
            <div className="mpj-connect-error">{error}</div>
          )}
        </div>
      </div>
    );
  }

  // ===== 已连接状态 =====
  return (
    <div className="mpj-container">
      {/* 顶部标题栏 */}
      <header className="mpj-header">
        <h1 className="mpj-title">马屁精来喽！</h1>
        <button onClick={disconnect} className="mpj-disconnect-btn">断开</button>
      </header>

      {/* 对话区域 */}
      <div className="mpj-chat-area" ref={chatAreaRef}>
        {messages.map(msg => (
          <div key={msg.id} className={`mpj-message ${msg.role}`}>
            <div className="mpj-message-role">{msg.role === 'user' ? '你' : '马屁精'}</div>
            <div className="mpj-message-text">{msg.text}</div>
          </div>
        ))}

        {currentText && (
          <div className={`mpj-message ${currentTextRole} current`}>
            <div className="mpj-message-role">
              {currentTextRole === 'user' ? '你' : '马屁精'}
            </div>
            <div className="mpj-message-text">{currentText}</div>
          </div>
        )}

        {messages.length === 0 && !currentText && (
          <div className="mpj-chat-empty">开始对话吧～</div>
        )}
      </div>

      {/* 底部操作区 */}
      <div className="mpj-input-area">
        {isBusy ? (
          /* 处理中 / AI说话中 */
          <div className="mpj-busy-bar">
            <span className="mpj-busy-label">
              {sessionState === 'speaking' ? 'AI 说话中...' : '处理中...'}
            </span>
            <button onClick={interrupt} className="mpj-btn mpj-btn-interrupt">
              打断
            </button>
          </div>
        ) : sessionState === 'listening' ? (
          /* 录音中 */
          <div className="mpj-recording-bar">
            <div className="mpj-recording-indicator">
              <span className="mpj-recording-dot" />
              <span>正在聆听...</span>
            </div>
            <button
              onMouseUp={stopRecording}
              onMouseLeave={stopRecording}
              onTouchEnd={stopRecording}
              className="mpj-btn mpj-btn-release"
            >
              松开结束
            </button>
          </div>
        ) : (
          /* 已连接，待命 */
          <div className="mpj-input-bar">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendText()}
              placeholder="输入消息..."
              className="mpj-text-input"
            />
            <button
              onClick={sendText}
              disabled={!inputText.trim()}
              className="mpj-btn mpj-btn-send"
            >
              发送
            </button>
            <button
              onMouseDown={startRecording}
              onMouseUp={stopRecording}
              onMouseLeave={stopRecording}
              onTouchStart={startRecording}
              onTouchEnd={stopRecording}
              className="mpj-btn mpj-btn-talk"
            >
              按住说话
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Mapijing;
