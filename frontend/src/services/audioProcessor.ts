/**
 * 音频处理模块
 * 提供降采样、格式转换等功能
 */

/**
 * 降采样函数
 * @param buffer 原始音频数据 Float32Array
 * @param fromSampleRate 原始采样率
 * @param toSampleRate 目标采样率（16000）
 */
export function downsampleBuffer(
  buffer: Float32Array,
  fromSampleRate: number,
  toSampleRate: number
): Float32Array {
  if (fromSampleRate === toSampleRate) {
    return buffer;
  }

  const ratio = fromSampleRate / toSampleRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    // 使用平均值进行降采样以获得更好的质量
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), buffer.length);
    let sum = 0;
    let count = 0;
    for (let j = start; j < end; j++) {
      sum += buffer[j];
      count++;
    }
    result[i] = count > 0 ? sum / count : 0;
  }

  return result;
}

/**
 * Float32 转 Int16 PCM
 * @param float32Array Float32 音频数据
 */
export function float32ToInt16(float32Array: Float32Array): Int16Array {
  const int16Array = new Int16Array(float32Array.length);

  for (let i = 0; i < float32Array.length; i++) {
    // 限制范围 [-1, 1]
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    // 转换为 Int16
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  return int16Array;
}

/**
 * Int16Array 转 Base64
 */
export function int16ToBase64(int16Array: Int16Array): string {
  const uint8Array = new Uint8Array(int16Array.buffer);
  let binary = '';
  for (let i = 0; i < uint8Array.length; i++) {
    binary += String.fromCharCode(uint8Array[i]);
  }
  return btoa(binary);
}

/**
 * 处理音频数据：降采样 + 格式转换 + Base64 编码
 */
export function processAudioData(buffer: Float32Array, fromSampleRate: number): string {
  const downsampled = downsampleBuffer(buffer, fromSampleRate, 16000);
  const int16Data = float32ToInt16(downsampled);
  return int16ToBase64(int16Data);
}

/**
 * Int16Array 转 Uint8Array（用于二进制协议）
 */
export function int16ToUint8(int16Array: Int16Array): Uint8Array {
  return new Uint8Array(int16Array.buffer);
}

/**
 * 处理音频数据并返回 Uint8Array（用于二进制协议）
 */
export function processAudioDataToBytes(buffer: Float32Array, fromSampleRate: number): Uint8Array {
  const downsampled = downsampleBuffer(buffer, fromSampleRate, 16000);
  const int16Data = float32ToInt16(downsampled);
  return int16ToUint8(int16Data);
}
