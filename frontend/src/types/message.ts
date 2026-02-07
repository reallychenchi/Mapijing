/**
 * WebSocket 消息类型定义
 */

// 消息方向
export type MessageDirection = 'client_to_server' | 'server_to_client';

// 客户端发送的消息类型
export type ClientMessageType = 'audio_data' | 'audio_end' | 'interrupt';

// 服务端发送的消息类型
export type ServerMessageType =
  | 'asr_result'
  | 'asr_end'
  | 'tts_chunk'
  | 'tts_end'
  | 'emotion'
  | 'error';

// 错误码
export type ErrorCode =
  | 'ASR_ERROR'
  | 'LLM_ERROR'
  | 'TTS_ERROR'
  | 'NETWORK_ERROR'
  | 'UNKNOWN_ERROR';

// 情感类型（服务端返回的中文值）
export type ServerEmotion = '默认陪伴' | '共情倾听' | '安慰支持' | '轻松愉悦';

// 基础消息结构
export interface BaseMessage<T extends string, D = unknown> {
  type: T;
  data: D;
  timestamp?: number;
}

// === 客户端消息 ===

export type AudioDataMessage = BaseMessage<
  'audio_data',
  {
    audio: string; // base64 encoded PCM
    seq: number;
  }
>;

export type AudioEndMessage = BaseMessage<'audio_end', Record<string, never>>;

export type InterruptMessage = BaseMessage<'interrupt', Record<string, never>>;

export type ClientMessage = AudioDataMessage | AudioEndMessage | InterruptMessage;

// === 服务端消息 ===

export type AsrResultMessage = BaseMessage<
  'asr_result',
  {
    text: string;
    is_final: boolean;
  }
>;

export type AsrEndMessage = BaseMessage<
  'asr_end',
  {
    text: string;
  }
>;

export type TtsChunkMessage = BaseMessage<
  'tts_chunk',
  {
    text: string;
    audio: string; // base64 encoded MP3
    seq: number;
    is_final: boolean;
  }
>;

export type TtsEndMessage = BaseMessage<
  'tts_end',
  {
    full_text: string;
  }
>;

export type EmotionMessage = BaseMessage<
  'emotion',
  {
    emotion: ServerEmotion;
  }
>;

export type ErrorMessage = BaseMessage<
  'error',
  {
    code: ErrorCode;
    message: string;
  }
>;

export type ServerMessage =
  | AsrResultMessage
  | AsrEndMessage
  | TtsChunkMessage
  | TtsEndMessage
  | EmotionMessage
  | ErrorMessage;

// 创建客户端消息的辅助函数
export function createAudioDataMessage(audio: string, seq: number): AudioDataMessage {
  return {
    type: 'audio_data',
    data: { audio, seq },
  };
}

export function createAudioEndMessage(): AudioEndMessage {
  return {
    type: 'audio_end',
    data: {},
  };
}

export function createInterruptMessage(): InterruptMessage {
  return {
    type: 'interrupt',
    data: {},
  };
}
