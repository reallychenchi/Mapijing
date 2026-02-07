import { describe, it, expect } from 'vitest';
import {
  createAudioDataMessage,
  createAudioEndMessage,
  createInterruptMessage,
} from './message';
import type {
  ClientMessage,
  ServerMessage,
  AsrResultMessage,
  ErrorMessage,
} from './message';

describe('message types', () => {
  describe('createAudioDataMessage', () => {
    it('should create audio data message with correct structure', () => {
      const message = createAudioDataMessage('base64audio', 1);

      expect(message.type).toBe('audio_data');
      expect(message.data.audio).toBe('base64audio');
      expect(message.data.seq).toBe(1);
    });
  });

  describe('createAudioEndMessage', () => {
    it('should create audio end message with correct structure', () => {
      const message = createAudioEndMessage();

      expect(message.type).toBe('audio_end');
      expect(message.data).toEqual({});
    });
  });

  describe('createInterruptMessage', () => {
    it('should create interrupt message with correct structure', () => {
      const message = createInterruptMessage();

      expect(message.type).toBe('interrupt');
      expect(message.data).toEqual({});
    });
  });

  describe('type definitions', () => {
    it('should accept valid client messages', () => {
      const messages: ClientMessage[] = [
        { type: 'audio_data', data: { audio: 'test', seq: 1 } },
        { type: 'audio_end', data: {} },
        { type: 'interrupt', data: {} },
      ];

      expect(messages).toHaveLength(3);
    });

    it('should accept valid server messages', () => {
      const messages: ServerMessage[] = [
        { type: 'asr_result', data: { text: 'hello', is_final: false } },
        { type: 'asr_end', data: { text: 'hello world' } },
        { type: 'tts_chunk', data: { text: 'hi', audio: 'mp3', seq: 1, is_final: false } },
        { type: 'tts_end', data: { full_text: 'hi there' } },
        { type: 'emotion', data: { emotion: '默认陪伴' } },
        { type: 'error', data: { code: 'UNKNOWN_ERROR', message: 'test error' } },
      ];

      expect(messages).toHaveLength(6);
    });
  });

  describe('message serialization', () => {
    it('should serialize client message to JSON correctly', () => {
      const message = createAudioDataMessage('dGVzdA==', 5);
      const json = JSON.stringify(message);
      const parsed = JSON.parse(json);

      expect(parsed.type).toBe('audio_data');
      expect(parsed.data.audio).toBe('dGVzdA==');
      expect(parsed.data.seq).toBe(5);
    });

    it('should parse server message from JSON correctly', () => {
      const json = '{"type":"asr_result","data":{"text":"你好","is_final":true},"timestamp":1234567890}';
      const message: AsrResultMessage = JSON.parse(json);

      expect(message.type).toBe('asr_result');
      expect(message.data.text).toBe('你好');
      expect(message.data.is_final).toBe(true);
      expect(message.timestamp).toBe(1234567890);
    });

    it('should parse error message from JSON correctly', () => {
      const json = '{"type":"error","data":{"code":"ASR_ERROR","message":"识别失败"}}';
      const message: ErrorMessage = JSON.parse(json);

      expect(message.type).toBe('error');
      expect(message.data.code).toBe('ASR_ERROR');
      expect(message.data.message).toBe('识别失败');
    });
  });
});
