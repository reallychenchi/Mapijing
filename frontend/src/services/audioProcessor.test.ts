import { describe, it, expect } from 'vitest';
import {
  downsampleBuffer,
  float32ToInt16,
  int16ToBase64,
  processAudioData,
  int16ToUint8,
  processAudioDataToBytes,
} from './audioProcessor';

describe('audioProcessor', () => {
  describe('downsampleBuffer', () => {
    it('should return same buffer when sample rates are equal', () => {
      const buffer = new Float32Array([0.1, 0.2, 0.3, 0.4]);
      const result = downsampleBuffer(buffer, 16000, 16000);
      expect(result).toBe(buffer);
    });

    it('should downsample from 48kHz to 16kHz', () => {
      // 48kHz to 16kHz = 3:1 ratio
      const buffer = new Float32Array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]);
      const result = downsampleBuffer(buffer, 48000, 16000);
      expect(result.length).toBe(2);
    });

    it('should downsample from 44.1kHz to 16kHz', () => {
      // Create a buffer with 44100 samples
      const buffer = new Float32Array(441);
      for (let i = 0; i < 441; i++) {
        buffer[i] = Math.sin(i / 10);
      }
      const result = downsampleBuffer(buffer, 44100, 16000);
      // 441 / (44100/16000) ≈ 160
      expect(result.length).toBe(160);
    });

    it('should handle empty buffer', () => {
      const buffer = new Float32Array(0);
      const result = downsampleBuffer(buffer, 48000, 16000);
      expect(result.length).toBe(0);
    });
  });

  describe('float32ToInt16', () => {
    it('should convert positive values', () => {
      const float32 = new Float32Array([0.5]);
      const result = float32ToInt16(float32);
      // 0.5 * 0x7fff = 16383.5 ≈ 16383
      expect(result[0]).toBe(Math.floor(0.5 * 0x7fff));
    });

    it('should convert negative values', () => {
      const float32 = new Float32Array([-0.5]);
      const result = float32ToInt16(float32);
      // -0.5 * 0x8000 = -16384
      expect(result[0]).toBe(-0.5 * 0x8000);
    });

    it('should clamp values above 1', () => {
      const float32 = new Float32Array([1.5]);
      const result = float32ToInt16(float32);
      // Clamped to 1, then 1 * 0x7fff = 32767
      expect(result[0]).toBe(0x7fff);
    });

    it('should clamp values below -1', () => {
      const float32 = new Float32Array([-1.5]);
      const result = float32ToInt16(float32);
      // Clamped to -1, then -1 * 0x8000 = -32768
      expect(result[0]).toBe(-0x8000);
    });

    it('should handle zero', () => {
      const float32 = new Float32Array([0]);
      const result = float32ToInt16(float32);
      expect(result[0]).toBe(0);
    });
  });

  describe('int16ToBase64', () => {
    it('should convert Int16Array to base64', () => {
      const int16 = new Int16Array([1, 2, 3]);
      const result = int16ToBase64(int16);
      // Should be a valid base64 string
      expect(typeof result).toBe('string');
      expect(result.length).toBeGreaterThan(0);
    });

    it('should handle empty array', () => {
      const int16 = new Int16Array(0);
      const result = int16ToBase64(int16);
      expect(result).toBe('');
    });

    it('should produce decodable base64', () => {
      const int16 = new Int16Array([256, 512]);
      const base64 = int16ToBase64(int16);
      // Decode back
      const decoded = atob(base64);
      expect(decoded.length).toBe(4); // 2 Int16 = 4 bytes
    });
  });

  describe('int16ToUint8', () => {
    it('should convert Int16Array to Uint8Array', () => {
      const int16 = new Int16Array([256]);
      const result = int16ToUint8(int16);
      expect(result).toBeInstanceOf(Uint8Array);
      expect(result.length).toBe(2); // 1 Int16 = 2 bytes
    });
  });

  describe('processAudioData', () => {
    it('should process audio and return base64', () => {
      const buffer = new Float32Array(480); // 30ms at 16kHz
      for (let i = 0; i < 480; i++) {
        buffer[i] = Math.sin(i / 10) * 0.5;
      }
      const result = processAudioData(buffer, 16000);
      expect(typeof result).toBe('string');
      expect(result.length).toBeGreaterThan(0);
    });

    it('should downsample and convert from 48kHz', () => {
      const buffer = new Float32Array(4800); // 100ms at 48kHz
      for (let i = 0; i < 4800; i++) {
        buffer[i] = Math.sin(i / 10) * 0.5;
      }
      const result = processAudioData(buffer, 48000);
      expect(typeof result).toBe('string');
      // Downsampled to 16kHz = 1600 samples = 3200 bytes
      // Base64 encoding adds ~33% overhead
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('processAudioDataToBytes', () => {
    it('should process audio and return Uint8Array', () => {
      const buffer = new Float32Array(480);
      for (let i = 0; i < 480; i++) {
        buffer[i] = Math.sin(i / 10) * 0.5;
      }
      const result = processAudioDataToBytes(buffer, 16000);
      expect(result).toBeInstanceOf(Uint8Array);
      expect(result.length).toBe(960); // 480 samples * 2 bytes per sample
    });
  });
});
