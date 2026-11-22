import type { ConnectionStatus, TranscriptMessage, FunctionCall, FunctionResult, LanguageCode } from '@/types';
import { AudioProcessor, AudioPlayer, AUDIO_CONFIG, pcmToBase64, base64ToPcm } from '@utils/audio';

export interface LiveMessage {
  type: 'setup' | 'audio' | 'text' | 'function_call' | 'function_response' | 'interrupt' | 'error' | 'close';
  payload?: unknown;
}

export interface LiveConfig {
  sessionId: string;
  token: string;
  language: LanguageCode;
  voiceName: string;
  systemInstruction: string;
  onStatusChange: (status: ConnectionStatus) => void;
  onTranscript: (message: TranscriptMessage) => void;
  onAudioResponse: (audio: Int16Array) => void;
  onFunctionCall: (call: FunctionCall) => void;
  onError: (error: string) => void;
}

export class LiveWebSocketService {
  private ws: WebSocket | null = null;
  private audioProcessor: AudioProcessor;
  private audioPlayer: AudioPlayer;
  private config: LiveConfig | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 1000;
  private isIntentionalClose = false;
  private pendingAudioChunks: Int16Array[] = [];
  private recognition: any = null;
  private hasReceivedAudioThisTurn = false;
  private hasNativeAudioStream = false;

  constructor() {
    this.audioProcessor = new AudioProcessor();
    this.audioPlayer = new AudioPlayer(() => {
      if (this.config && this.hasReceivedAudioThisTurn) {
        this.hasReceivedAudioThisTurn = false;
        this.config.onStatusChange('listening');
      }
    });
  }

  async connect(config: LiveConfig): Promise<void> {
    this.config = config;
    this.isIntentionalClose = false;
    this.reconnectAttempts = 0;
    this.hasReceivedAudioThisTurn = false;
    this.hasNativeAudioStream = false;

    try {
      config.onStatusChange('requesting_permission');
      await this.startAudioCapture();

      config.onStatusChange('connecting');

      const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/live/${config.sessionId}?token=${config.token}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.sendSetup();
        config.onStatusChange('connected');
        this.startSpeechRecognition(config);
        config.onStatusChange('listening');
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event);
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        config.onError('Connection error');
      };

      this.ws.onclose = (event: CloseEvent) => {
        this.stopSpeechRecognition();
        if (!this.isIntentionalClose) {
          if (event.code === 1008 || event.code === 1011) {
            config.onStatusChange('error');
            config.onError(event.reason || 'Server connection closed unexpectedly');
          } else {
            this.handleUnexpectedClose(config);
          }
        } else {
          config.onStatusChange('disconnected');
        }
      };
    } catch (error) {
      config.onError(error instanceof Error ? error.message : 'Failed to connect');
      config.onStatusChange('error');
      throw error;
    }
  }

  private sendSetup(): void {
    if (!this.ws || !this.config) return;

    const setupMessage = {
      type: 'setup',
      payload: {
        language: this.config.language,
        voice_name: this.config.voiceName,
        system_instruction: this.config.systemInstruction,
        sample_rate: AUDIO_CONFIG.sampleRate,
      },
    };

    this.ws.send(JSON.stringify(setupMessage));
  }

  private startSpeechRecognition(config: LiveConfig): void {
    if (typeof window === 'undefined') return;
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) return;

    try {
      this.recognition = new SpeechRec();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = config.language;

      this.recognition.onresult = (event: any) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            const trimmed = transcript.trim();
            if (trimmed) {
              const userMsg: TranscriptMessage = {
                id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                speaker: 'user',
                text: trimmed,
                language: config.language,
                timestamp: Date.now(),
                isFinal: true,
              };
              config.onTranscript(userMsg);
              // PREVENT DUPLICATE USER TURNS:
              // Only send text turn over WebSocket if live audio capture is NOT active
              if (!this.audioProcessor.getIsRecording()) {
                this.sendTextMessage(trimmed);
              }
            }
          }
        }
      };

      this.recognition.onerror = (e: any) => {
        console.warn('SpeechRecognition error:', e);
      };

      this.recognition.onend = () => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN && !this.isIntentionalClose) {
          try {
            this.recognition.start();
          } catch {
            // Already active or error
          }
        }
      };

      this.recognition.start();
    } catch (e) {
      console.warn('SpeechRecognition initialization skipped:', e);
    }
  }

  private stopSpeechRecognition(): void {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {
        // Ignore abort errors
      }
      this.recognition = null;
    }
  }

  private async startAudioCapture(): Promise<void> {
    if (!this.config) return;

    await this.audioProcessor.startRecording((chunk) => {
      this.sendAudioChunk(chunk);
    });
  }

  private sendAudioChunk(chunk: { data: Int16Array; timestamp: number; isFinal: boolean }): void {
    this.hasReceivedAudioThisTurn = false;
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.pendingAudioChunks.push(chunk.data);
      return;
    }

    while (this.pendingAudioChunks.length > 0) {
      const pending = this.pendingAudioChunks.shift()!;
      this.sendAudioData(pending);
    }

    this.sendAudioData(chunk.data);
  }

  private sendAudioData(data: Int16Array): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const base64Audio = pcmToBase64(data);
    this.ws.send(JSON.stringify({
      type: 'audio',
      payload: { data: base64Audio, mime_type: 'audio/pcm;rate=16000' },
    }));
  }

  sendTextMessage(text: string): void {
    this.hasReceivedAudioThisTurn = false;
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    this.ws.send(JSON.stringify({
      type: 'text',
      payload: { text },
    }));
  }

  private handleMessage(event: MessageEvent): void {
    if (!this.config) return;

    try {
      const message = JSON.parse(event.data) as LiveMessage;

      switch (message.type) {
        case 'audio':
          this.handleAudioResponse(message.payload as { data: string });
          break;
        case 'text':
          this.handleTextResponse(message.payload as { text: string; is_final: boolean; speaker: 'user' | 'assistant' });
          break;
        case 'function_call':
          this.handleFunctionCall(message.payload as FunctionCall);
          break;
        case 'interrupt':
          this.handleInterruption();
          break;
        case 'error':
          this.config.onError(message.payload as string);
          this.config.onStatusChange('error');
          break;
        case 'close':
          this.close();
          break;
        default:
          console.warn('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Failed to parse message:', error);
    }
  }

  private handleAudioResponse(payload: { data: string }): void {
    if (!this.config) return;

    try {
      this.hasReceivedAudioThisTurn = true;
      this.hasNativeAudioStream = true;
      const pcmData = base64ToPcm(payload.data);
      this.config.onAudioResponse(pcmData);
      this.audioPlayer.playAudio(pcmData, 24000);
      this.config.onStatusChange('speaking');
    } catch (error) {
      console.error('Audio playback error:', error);
    }
  }

  private handleTextResponse(payload: { text: string; is_final: boolean; speaker: 'user' | 'assistant' }): void {
    if (!this.config) return;

    const transcript: TranscriptMessage = {
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      speaker: payload.speaker,
      text: payload.text,
      language: this.config.language,
      timestamp: Date.now(),
      isFinal: payload.is_final,
    };

    this.config.onTranscript(transcript);

    if (payload.speaker === 'assistant' && payload.is_final) {
      // PREVENT BROWSER TTS COLLISION:
      // Suppress speakText if native Gemini Live PCM audio stream is active or received
      if (!this.hasReceivedAudioThisTurn && !this.hasNativeAudioStream && !this.audioPlayer.getIsPlaying()) {
        this.speakText(payload.text, this.config.language);
      }
    }
  }

  private speakText(text: string, language: LanguageCode): void {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      this.config?.onStatusChange('listening');
      return;
    }

    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = language;
      utterance.volume = this.audioPlayer.getVolume();

      utterance.onstart = () => {
        this.config?.onStatusChange('speaking');
      };
      utterance.onend = () => {
        this.config?.onStatusChange('listening');
      };
      utterance.onerror = () => {
        this.config?.onStatusChange('listening');
      };

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('SpeechSynthesis error:', e);
      this.config?.onStatusChange('listening');
    }
  }

  private handleFunctionCall(call: FunctionCall): void {
    if (!this.config) return;
    this.config.onFunctionCall(call);
  }

  private handleInterruption(): void {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.hasReceivedAudioThisTurn = false;
    this.audioPlayer.stop();
    this.audioPlayer.clearQueue();
    this.config?.onStatusChange('listening');
  }

  private async handleUnexpectedClose(config: LiveConfig): Promise<void> {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      config.onStatusChange('reconnecting');
      await new Promise(resolve => setTimeout(resolve, this.reconnectDelay * this.reconnectAttempts));
      try {
        await this.connect(config);
      } catch {
        config.onStatusChange('error');
        config.onError('Connection lost. Please click Try Again.');
      }
    } else {
      config.onStatusChange('error');
      config.onError('Connection lost. Please restart conversation.');
    }
  }

  sendFunctionResult(result: FunctionResult): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    this.ws.send(JSON.stringify({
      type: 'function_response',
      payload: result,
    }));
  }

  interrupt(): void {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.hasReceivedAudioThisTurn = false;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'interrupt' }));
    }
    this.audioPlayer.stop();
    this.audioPlayer.clearQueue();
    this.config?.onStatusChange('listening');
  }

  setVolume(volume: number): void {
    this.audioPlayer.setVolume(volume);
  }

  async close(): Promise<void> {
    this.isIntentionalClose = true;

    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.stopSpeechRecognition();
    this.audioProcessor.stopRecording();
    this.audioPlayer.destroy();

    if (this.ws) {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'close' }));
      }
      this.ws.close();
      this.ws = null;
    }

    this.config?.onStatusChange('disconnected');
    this.config = null;
  }

  getConnectionStatus(): ConnectionStatus {
    if (!this.ws) return 'disconnected';
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting';
      case WebSocket.OPEN: return 'connected';
      case WebSocket.CLOSING: return 'disconnected';
      case WebSocket.CLOSED: return 'disconnected';
      default: return 'disconnected';
    }
  }
}

export const liveService = new LiveWebSocketService();
