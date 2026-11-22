export const AUDIO_CONFIG = {
  sampleRate: 16000,
  channels: 1,
  bitDepth: 16,
  chunkSize: 4096,
} as const;

export interface AudioChunk {
  data: Int16Array;
  timestamp: number;
  isFinal: boolean;
}

export class AudioProcessor {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private zeroGain: GainNode | null = null;
  private onAudioData: ((chunk: AudioChunk) => void) | null = null;
  private isRecording = false;

  async startRecording(onAudioData: (chunk: AudioChunk) => void): Promise<void> {
    if (this.isRecording) return;

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: AUDIO_CONFIG.sampleRate,
          channelCount: AUDIO_CONFIG.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioCtx({
        sampleRate: AUDIO_CONFIG.sampleRate,
      });

      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.processor = this.audioContext.createScriptProcessor(
        AUDIO_CONFIG.chunkSize,
        AUDIO_CONFIG.channels,
        AUDIO_CONFIG.channels
      );

      // Acoustic Feedback Prevention:
      // Route ScriptProcessorNode through a GainNode with gain = 0 to destination.
      // Keeps processor node alive and firing onaudioprocess without feeding mic back to speakers.
      this.zeroGain = this.audioContext.createGain();
      this.zeroGain.gain.value = 0;

      this.onAudioData = onAudioData;
      this.isRecording = true;

      this.processor.onaudioprocess = (event) => {
        if (!this.isRecording || !this.onAudioData) return;

        const inputBuffer = event.inputBuffer;
        const inputData = inputBuffer.getChannelData(0);

        const int16Data = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        this.onAudioData({
          data: int16Data,
          timestamp: Date.now(),
          isFinal: false,
        });
      };

      source.connect(this.processor);
      this.processor.connect(this.zeroGain);
      this.zeroGain.connect(this.audioContext.destination);
    } catch (error) {
      this.cleanup();
      throw error;
    }
  }

  stopRecording(): void {
    this.isRecording = false;
    this.cleanup();
  }

  private cleanup(): void {
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.zeroGain) {
      this.zeroGain.disconnect();
      this.zeroGain = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.onAudioData = null;
  }

  getIsRecording(): boolean {
    return this.isRecording;
  }
}

export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private gainNode: GainNode | null = null;
  private activeSources: Set<AudioBufferSourceNode> = new Set();
  private nextPlayTime = 0;
  private isPlaying = false;
  private volume = 1;
  private onPlaybackEnded: (() => void) | null = null;

  constructor(onPlaybackEnded?: () => void) {
    if (onPlaybackEnded) {
      this.onPlaybackEnded = onPlaybackEnded;
    }
    if (typeof window !== 'undefined') {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        try {
          this.audioContext = new AudioCtx({ sampleRate: 24000 });
        } catch {
          this.audioContext = new AudioCtx();
        }
        this.gainNode = this.audioContext.createGain();
        this.gainNode.connect(this.audioContext.destination);
        this.gainNode.gain.value = this.volume;
      }
    }
  }

  setOnPlaybackEnded(callback: () => void): void {
    this.onPlaybackEnded = callback;
  }

  setVolume(volume: number): void {
    this.volume = Math.max(0, Math.min(1, volume));
    if (this.gainNode && this.audioContext) {
      try {
        this.gainNode.gain.setValueAtTime(this.volume, this.audioContext.currentTime);
      } catch {
        this.gainNode.gain.value = this.volume;
      }
    }
  }

  getVolume(): number {
    return this.volume;
  }

  getIsPlaying(): boolean {
    return this.isPlaying && this.activeSources.size > 0;
  }

  getQueueLength(): number {
    return this.activeSources.size;
  }

  async playAudio(pcmData: Int16Array, sampleRate = 24000): Promise<void> {
    if (!this.audioContext || !this.gainNode || pcmData.length === 0) return;

    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    const audioBuffer = this.audioContext.createBuffer(1, pcmData.length, sampleRate);
    const channelData = audioBuffer.getChannelData(0);

    for (let i = 0; i < pcmData.length; i++) {
      channelData[i] = pcmData[i] / 32768;
    }

    // Web Audio Timeline Scheduling:
    // Gapless scheduling using Math.max(currentTime, nextPlayTime) + buffer.duration
    const currentTime = this.audioContext.currentTime;
    const startTime = Math.max(currentTime, this.nextPlayTime);

    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.gainNode);

    this.activeSources.add(source);
    this.isPlaying = true;

    source.onended = () => {
      this.activeSources.delete(source);
      if (this.activeSources.size === 0) {
        this.isPlaying = false;
        if (this.onPlaybackEnded) {
          this.onPlaybackEnded();
        }
      }
    };

    source.start(startTime);
    this.nextPlayTime = startTime + audioBuffer.duration;
  }

  stop(): void {
    this.nextPlayTime = 0;
    this.isPlaying = false;

    for (const source of this.activeSources) {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // Source may already have ended or been disconnected
      }
    }
    this.activeSources.clear();
  }

  async pause(): Promise<void> {
    if (this.audioContext && this.audioContext.state === 'running') {
      await this.audioContext.suspend();
    }
  }

  async resume(): Promise<void> {
    if (this.audioContext && this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }
  }

  clearQueue(): void {
    this.stop();
  }

  destroy(): void {
    this.stop();
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.gainNode = null;
  }
}

export function convertSampleRate(
  buffer: Int16Array,
  fromRate: number,
  toRate: number
): Int16Array {
  if (fromRate === toRate) return buffer;

  const ratio = fromRate / toRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Int16Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const srcIndex = i * ratio;
    const index = Math.floor(srcIndex);
    const fraction = srcIndex - index;

    if (index + 1 < buffer.length) {
      const a = buffer[index];
      const b = buffer[index + 1];
      result[i] = Math.round(a + (b - a) * fraction);
    } else {
      result[i] = buffer[index];
    }
  }

  return result;
}

export function pcmToBase64(pcmData: Int16Array): string {
  const bytes = new Uint8Array(pcmData.buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function base64ToPcm(base64: string): Int16Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }

  // Ensure even byte length for Int16Array (2 bytes per sample)
  const byteLength = bytes.length - (bytes.length % 2);
  if (byteLength === 0) {
    return new Int16Array(0);
  }

  // Create a new aligned buffer to avoid RangeError from odd byteOffset or length
  const alignedBuffer = new ArrayBuffer(byteLength);
  const alignedView = new Uint8Array(alignedBuffer);
  alignedView.set(bytes.subarray(0, byteLength));

  return new Int16Array(alignedBuffer);
}