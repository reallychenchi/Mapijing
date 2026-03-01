/**
 * AudioWorklet processor — runs on dedicated audio thread.
 * Accumulates 128-frame chunks until 320 frames (20ms @ 16000Hz),
 * then transfers the buffer to the main thread with zero-copy.
 */
class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._targetFrames = 320; // 16000Hz × 0.02s = 320 samples = 20ms
  }

  process(inputs) {
    const input = inputs[0][0];
    if (!input) return true;

    for (let i = 0; i < input.length; i++) {
      this._buffer.push(input[i]);
    }

    while (this._buffer.length >= this._targetFrames) {
      const floats = new Float32Array(this._targetFrames);
      for (let i = 0; i < this._targetFrames; i++) {
        floats[i] = this._buffer[i];
      }
      this._buffer.splice(0, this._targetFrames);
      // Transfer ownership — zero-copy, no GC pressure
      this.port.postMessage({ pcmFloat32: floats }, [floats.buffer]);
    }

    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
