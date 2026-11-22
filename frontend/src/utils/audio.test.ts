import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { pcmToBase64, base64ToPcm, convertSampleRate, AudioPlayer, AudioProcessor } from './audio';

describe('Audio Utility Functions', () => {
  it('converts PCM data to Base64 and back', () => {
    const original = new Int16Array([0, 1000, -1000, 32767, -32768]);
    const base64 = pcmToBase64(original);
    expect(typeof base64).toBe('string');
    expect(base64.length).toBeGreaterThan(0);

    const reconstructed = base64ToPcm(base64);
    expect(reconstructed.length).toBe(original.length);
    for (let i = 0; i < original.length; i++) {
      expect(reconstructed[i]).toBe(original[i]);
    }
  });

  it('safely handles empty base64 string without RangeError', () => {
    const result = base64ToPcm('');
    expect(result.length).toBe(0);
  });

  it('safely handles odd-byte base64 strings without RangeError', () => {
    const oddBase64 = btoa('A');
    const result = base64ToPcm(oddBase64);
    expect(result.length).toBe(0);
  });

  it('converts sample rate correctly', () => {
    const input = new Int16Array([100, 200, 300, 400]);
    const downsampled = convertSampleRate(input, 16000, 8000);
    expect(downsampled.length).toBe(2);

    const same = convertSampleRate(input, 16000, 16000);
    expect(same).toBe(input);
  });
});

describe('AudioPlayer Web Audio Timeline Scheduling', () => {
  let player: AudioPlayer;
  let onEndedMock: () => void;

  beforeEach(() => {
    onEndedMock = vi.fn();
    player = new AudioPlayer(onEndedMock);
  });

  afterEach(() => {
    player.destroy();
    vi.clearAllMocks();
  });

  it('schedules consecutive audio buffers gaplessly on the timeline', async () => {
    // 2400 samples at 24000Hz = 0.1s buffer duration
    const chunk1 = new Int16Array(2400);
    const chunk2 = new Int16Array(2400);

    await player.playAudio(chunk1, 24000);
    expect(player.getIsPlaying()).toBe(true);
    expect(player.getQueueLength()).toBe(1);

    await player.playAudio(chunk2, 24000);
    expect(player.getQueueLength()).toBe(2);
  });

  it('instantly stops all active sources and resets timeline on stop()', async () => {
    const chunk = new Int16Array(4800);
    await player.playAudio(chunk, 24000);
    await player.playAudio(chunk, 24000);

    expect(player.getQueueLength()).toBe(2);
    player.stop();

    expect(player.getIsPlaying()).toBe(false);
    expect(player.getQueueLength()).toBe(0);
  });

  it('adjusts volume via gain node', () => {
    player.setVolume(0.5);
    expect(player.getVolume()).toBe(0.5);

    player.setVolume(1.5);
    expect(player.getVolume()).toBe(1);

    player.setVolume(-0.2);
    expect(player.getVolume()).toBe(0);
  });

  it('triggers onPlaybackEnded callback when all scheduled sources end', async () => {
    const chunk = new Int16Array(2400);
    await player.playAudio(chunk, 24000);

    // Trigger onended manually on the active source
    const sources = Array.from((player as any).activeSources as Set<any>);
    expect(sources.length).toBe(1);

    sources[0].onended();
    expect(player.getIsPlaying()).toBe(false);
    expect(onEndedMock).toHaveBeenCalledTimes(1);
  });

  it('pauses and resumes playback via AudioContext suspend and resume', async () => {
    const ctx = (player as any).audioContext;
    await player.pause();
    expect(ctx.suspend).toHaveBeenCalled();

    await player.resume();
    expect(ctx.resume).toHaveBeenCalled();
  });
});

describe('AudioProcessor Acoustic Feedback Prevention', () => {
  let processor: AudioProcessor;

  beforeEach(() => {
    processor = new AudioProcessor();
  });

  afterEach(() => {
    processor.stopRecording();
    vi.clearAllMocks();
  });

  it('routes ScriptProcessorNode through GainNode with gain 0 to prevent acoustic feedback', async () => {
    const onData = vi.fn();
    await processor.startRecording(onData);

    expect(processor.getIsRecording()).toBe(true);
    const zeroGain = (processor as any).zeroGain;
    expect(zeroGain).toBeDefined();
    expect(zeroGain.gain.value).toBe(0);
    expect(zeroGain.connect).toHaveBeenCalled();
  });

  it('cleans up processor, zeroGain, stream tracks, and closes AudioContext on stopRecording()', async () => {
    const onData = vi.fn();
    await processor.startRecording(onData);

    const zeroGain = (processor as any).zeroGain;
    const proc = (processor as any).processor;
    const ctx = (processor as any).audioContext;

    processor.stopRecording();

    expect(processor.getIsRecording()).toBe(false);
    expect(zeroGain.disconnect).toHaveBeenCalled();
    expect(proc.disconnect).toHaveBeenCalled();
    expect(ctx.close).toHaveBeenCalled();
    expect((processor as any).zeroGain).toBeNull();
    expect((processor as any).processor).toBeNull();
    expect((processor as any).audioContext).toBeNull();
  });
});
