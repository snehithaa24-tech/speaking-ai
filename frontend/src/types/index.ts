export type LanguageCode = 'en-IN' | 'hi-IN';

export interface Language {
  code: LanguageCode;
  name: string;
  nativeName: string;
  script: 'latin' | 'devanagari';
  flag: string;
  voiceCandidates: string[];
  direction: 'ltr' | 'rtl';
}

export const SUPPORTED_LANGUAGES: Language[] = [
  {
    code: 'en-IN',
    name: 'English (India)',
    nativeName: 'English',
    script: 'latin',
    flag: '🇮🇳',
    voiceCandidates: ['Kore', 'Aoede', 'Sulafat', 'Vindemiatrix'],
    direction: 'ltr',
  },
  {
    code: 'hi-IN',
    name: 'Hindi',
    nativeName: 'हिन्दी',
    script: 'devanagari',
    flag: '🇮🇳',
    voiceCandidates: ['Kore', 'Sulafat', 'Vindemiatrix', 'Erinome'],
    direction: 'ltr',
  },
];

export const DEFAULT_LANGUAGE: LanguageCode = 'en-IN';

export function getLanguage(code: LanguageCode): Language {
  return SUPPORTED_LANGUAGES.find(l => l.code === code) ?? SUPPORTED_LANGUAGES[0];
}

export type ConnectionStatus =
  | 'idle'
  | 'requesting_permission'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'reconnecting'
  | 'disconnected'
  | 'error';

export interface TranscriptMessage {
  id: string;
  speaker: 'user' | 'assistant';
  text: string;
  language: LanguageCode;
  timestamp: number;
  isFinal: boolean;
}

export interface VoiceSessionConfig {
  language: LanguageCode;
  voiceName: string;
  systemInstruction: string;
  temperature: number;
  maxOutputTokens: number;
}

export interface SessionState {
  status: ConnectionStatus;
  sessionId: string | null;
  transcripts: TranscriptMessage[];
  currentUserTranscript: string;
  currentAssistantTranscript: string;
  error: string | null;
  isMuted: boolean;
  volume: number;
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  category: KnowledgeCategory;
  sourceUrl: string;
  content: string;
  publishedAt: string;
  verifiedAt: string;
  language: LanguageCode;
}

export type KnowledgeCategory =
  | 'agriculture'
  | 'government_schemes'
  | 'transport'
  | 'hospital_assistance'
  | 'general';

export interface KnowledgeSearchResult {
  documents: KnowledgeDocument[];
  query: string;
  language: LanguageCode;
  totalResults: number;
}

export interface FunctionCall {
  name: string;
  args: Record<string, unknown>;
  id: string;
}

export interface FunctionResult {
  functionCallId: string;
  result: unknown;
  error?: string;
}

export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  success: boolean;
}

export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  preferredLanguage?: string;
}

export interface UserPreferences {
  language: LanguageCode;
  largeText: boolean;
  highContrast: boolean;
  reducedMotion: boolean;
  volume: number;
}

export interface SessionRecord {
  id: string;
  userId: string | null;
  startedAt: string;
  endedAt: string | null;
  status: 'active' | 'completed' | 'error' | 'interrupted';
  language: LanguageCode;
  messageCount: number;
}

export interface Feedback {
  id: string;
  sessionId: string;
  rating: 1 | 2 | 3 | 4 | 5;
  comment?: string;
  createdAt: string;
}

export interface EvaluationRecord {
  id: string;
  language: LanguageCode;
  testCategory: string;
  result: 'pass' | 'fail' | 'partial';
  measuredLatency: number;
  wordErrorRate: number;
  notes?: string;
  createdAt: string;
}