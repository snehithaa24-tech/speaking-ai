import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});

// Mock window.matchMedia for AccessibilityContext and responsive components
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock Element.prototype.scrollIntoView
if (typeof Element !== 'undefined') {
  Element.prototype.scrollIntoView = vi.fn();
}

// Mock Web Audio API
export class MockAudioGainNode {
  gain = {
    value: 1,
    setValueAtTime: vi.fn((val: number) => {
      this.gain.value = val;
    }),
  };
  connect = vi.fn();
  disconnect = vi.fn();
}

export class MockAudioBufferSourceNode {
  buffer: any = null;
  connect = vi.fn();
  disconnect = vi.fn();
  start = vi.fn();
  stop = vi.fn();
  onended: (() => void) | null = null;
}

export class MockAudioContext {
  currentTime = 0;
  sampleRate = 24000;
  state: 'suspended' | 'running' | 'closed' = 'running';
  destination = {};

  createGain = vi.fn(() => new MockAudioGainNode());
  createBufferSource = vi.fn(() => new MockAudioBufferSourceNode());
  createBuffer = vi.fn((channels: number, length: number, sampleRate: number) => ({
    duration: length / sampleRate,
    length,
    numberOfChannels: channels,
    sampleRate,
    getChannelData: vi.fn(() => new Float32Array(length)),
    copyToChannel: vi.fn(),
  }));
  createScriptProcessor = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    onaudioprocess: null,
  }));
  createMediaStreamSource = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  }));
  resume = vi.fn().mockImplementation(async () => {
    this.state = 'running';
  });
  suspend = vi.fn().mockImplementation(async () => {
    this.state = 'suspended';
  });
  close = vi.fn().mockImplementation(async () => {
    this.state = 'closed';
  });
}

(globalThis as any).AudioContext = MockAudioContext;
(globalThis as any).webkitAudioContext = MockAudioContext;

// Mock navigator.mediaDevices.getUserMedia
if (typeof navigator !== 'undefined') {
  if (!navigator.mediaDevices) {
    (navigator as any).mediaDevices = {};
  }
  navigator.mediaDevices.getUserMedia = vi.fn().mockResolvedValue({
    getTracks: () => [
      {
        stop: vi.fn(),
        kind: 'audio',
        enabled: true,
      },
    ],
  });
}
