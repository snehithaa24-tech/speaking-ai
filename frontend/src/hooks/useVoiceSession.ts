import { useState, useCallback, useRef, useEffect } from 'react';
import { useLanguage } from '@contexts/LanguageContext';
import { useAccessibility } from '@contexts/AccessibilityContext';
import { apiService } from '@services/api';
import { liveService, LiveConfig } from '@services/websocket';
import type { ConnectionStatus, TranscriptMessage, VoiceSessionConfig, FunctionCall, FunctionResult, LanguageCode } from '@/types';
import { getLanguage } from '@/types';

const SYSTEM_INSTRUCTIONS: Record<LanguageCode, string> = {
  'en-IN': `You are Sahayak AI, a helpful voice assistant for accessibility. Respond naturally and clearly in Indian English. Use simple vocabulary. Speak in short sentences. Be patient and respectful. If the user asks for something you cannot do, explain what you can help with instead. Never pretend to have completed an external action.`,
  'hi-IN': `आप सहायक AI हैं, एक सहायक और सुगम्यता वॉयस असिस्टेंट। प्राकृतिक और स्पष्ट हिंदी में जवाब दें। सरल शब्दावली का उपयोग करें। छोटे वाक्यों में बोलें। धैर्यवान और सम्मानजनक रहें। यदि उपयोगकर्ता कुछ ऐसा पूछता है जो आप नहीं कर सकते, तो बताएं कि आप किसमें मदद कर सकते हैं। कभी भी यह दिखावा न करें कि आपने कोई बाहरी कार्रवाई पूरी कर ली है।`,
};

const VOICE_NAMES: Record<LanguageCode, string> = {
  'en-IN': 'Kore',
  'hi-IN': 'Kore',
};

export function useVoiceSession() {
  const { languageCode, t } = useLanguage();
  const { settings: accessibilitySettings } = useAccessibility();

  const [status, setStatus] = useState<ConnectionStatus>('idle');
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([]);
  const [currentUserTranscript, setCurrentUserTranscript] = useState('');
  const [currentAssistantTranscript, setCurrentAssistantTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);

  const pendingFunctionCalls = useRef<Map<string, FunctionCall>>(new Map());
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    liveService.setVolume(accessibilitySettings.volume);
    return () => { isMounted.current = false; };
  }, [accessibilitySettings.volume]);

  const handleStatusChange = useCallback((newStatus: ConnectionStatus) => {
    if (!isMounted.current) return;
    setStatus(newStatus);
    if (newStatus === 'error' || newStatus === 'disconnected' || newStatus === 'idle') {
      setCurrentUserTranscript('');
      setCurrentAssistantTranscript('');
    }
  }, []);

  const handleTranscript = useCallback((message: TranscriptMessage) => {
    if (!isMounted.current) return;
    setTranscripts(prev => [...prev, message]);
    if (message.speaker === 'user') {
      setCurrentUserTranscript(message.text);
    } else {
      setCurrentAssistantTranscript(message.text);
    }
  }, []);

  const handleAudioResponse = useCallback(() => {
    if (!isMounted.current) return;
  }, []);

  const handleFunctionCall = useCallback((call: FunctionCall) => {
    if (!isMounted.current) return;
    pendingFunctionCalls.current.set(call.id, call);
    executeFunctionCall(call);
  }, []);

  const handleError = useCallback((errorMessage: string) => {
    if (!isMounted.current) return;
    setError(errorMessage);
  }, []);

  const executeFunctionCall = useCallback(async (call: FunctionCall) => {
    try {
      let result: unknown;

      switch (call.name) {
        case 'search_knowledge': {
          const { query, category, language } = call.args as { query: string; category?: string; language?: string };
          const response = await apiService.searchKnowledge(query, category as any, language || languageCode, 5);
          result = response.data || { documents: [], totalResults: 0 };
          break;
        }
        case 'get_scheme_details': {
          const { schemeId } = call.args as { schemeId: string };
          const response = await apiService.getDocument(schemeId);
          result = response.data || { error: 'Scheme not found' };
          break;
        }
        case 'find_nearby_hospital': {
          const args = call.args as { location?: string; specialty?: string };
          void args;
          result = { hospitals: [], message: 'Location-based search requires backend implementation' };
          break;
        }
        case 'get_transport_information': {
          const args = call.args as { from?: string; to?: string; mode?: string };
          void args;
          result = { routes: [], message: 'Transport integration requires backend implementation' };
          break;
        }
        case 'repeat_last_answer': {
          const lastAssistant = [...transcripts].reverse().find(t => t.speaker === 'assistant' && t.isFinal);
          result = { text: lastAssistant?.text || 'No previous answer to repeat' };
          break;
        }
        default:
          result = { error: `Unknown function: ${call.name}` };
      }

      const functionResult: FunctionResult = {
        functionCallId: call.id,
        result,
      };

      liveService.sendFunctionResult(functionResult);
      pendingFunctionCalls.current.delete(call.id);
    } catch (err) {
      const functionResult: FunctionResult = {
        functionCallId: call.id,
        result: null,
        error: err instanceof Error ? err.message : 'Function execution failed',
      };
      liveService.sendFunctionResult(functionResult);
      pendingFunctionCalls.current.delete(call.id);
    }
  }, [languageCode, transcripts]);

  const startSession = useCallback(async () => {
    if (status !== 'idle' && status !== 'disconnected' && status !== 'error') return;

    setError(null);
    setTranscripts([]);
    setCurrentUserTranscript('');
    setCurrentAssistantTranscript('');
    setStatus('requesting_permission');

    getLanguage(languageCode); // validate language code
    const config: VoiceSessionConfig = {
      language: languageCode,
      voiceName: VOICE_NAMES[languageCode],
      systemInstruction: SYSTEM_INSTRUCTIONS[languageCode],
      temperature: 0.7,
      maxOutputTokens: 2048,
    };

    try {
      const response = await apiService.createSession(config);
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to create session');
      }

      const newSessionId = response.data.sessionId;
      setSessionId(newSessionId);

      const liveConfig: LiveConfig = {
        sessionId: newSessionId,
        token: response.data.token,
        language: languageCode,
        voiceName: VOICE_NAMES[languageCode],
        systemInstruction: SYSTEM_INSTRUCTIONS[languageCode],
        onStatusChange: handleStatusChange,
        onTranscript: handleTranscript,
        onAudioResponse: handleAudioResponse,
        onFunctionCall: handleFunctionCall,
        onError: handleError,
      };

      await liveService.connect(liveConfig);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error.api'));
      setStatus('error');
    }
  }, [languageCode, status, handleStatusChange, handleTranscript, handleAudioResponse, handleFunctionCall, handleError, t]);

  const endSession = useCallback(async () => {
    if (sessionId) {
      await apiService.endSession(sessionId).catch(console.error);
    }
    await liveService.close();
    setSessionId(null);
    setStatus('disconnected');
  }, [sessionId]);

  const interrupt = useCallback(() => {
    liveService.interrupt();
    setCurrentAssistantTranscript('');
    setStatus('listening');
  }, []);

  const repeatLastAnswer = useCallback(() => {
    const lastAssistant = [...transcripts].reverse().find(t => t.speaker === 'assistant' && t.isFinal);
    if (lastAssistant) {
      setCurrentAssistantTranscript(lastAssistant.text);
    }
  }, [transcripts]);

  const toggleMute = useCallback(() => {
    setIsMuted(prev => !prev);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    status,
    transcripts,
    currentUserTranscript,
    currentAssistantTranscript,
    error,
    sessionId,
    isMuted,
    startSession,
    endSession,
    interrupt,
    repeatLastAnswer,
    toggleMute,
    clearError,
  };
}