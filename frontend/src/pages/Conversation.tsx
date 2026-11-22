import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { X, Volume2, VolumeX, RotateCcw, LogOut, Loader2 } from 'lucide-react';
import { useLanguage } from '@contexts/LanguageContext';
import { useAuth } from '@contexts/AuthContext';
import { useVoiceSession } from '@hooks/useVoiceSession';
import { Button } from '@components/shared/Button';
import { MicrophoneButton } from '@components/voice/MicrophoneButton';
import { Transcript } from '@components/voice/Transcript';
import { ConnectionStatus, ConnectionStatusDetailed } from '@components/voice/ConnectionStatus';
import { LanguageSelector } from '@components/accessibility/LanguageSelector';
import { AccessibilitySettings } from '@components/accessibility/AccessibilitySettings';
import { getLanguage, LanguageCode } from '@/types';

export function Conversation() {
  const { t, languageCode, setLanguage } = useLanguage();
  const { isAuthenticated, logout, login } = useAuth();
  const [searchParams] = useSearchParams();
  const language = getLanguage(languageCode);

  const {
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
  } = useVoiceSession();

  const [showSettings, setShowSettings] = useState(false);
  const [showAccessibility, setShowAccessibility] = useState(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const micButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts, currentUserTranscript, currentAssistantTranscript]);

  useEffect(() => {
    const category = searchParams.get('category');
    if (category && (status === 'idle' || status === 'disconnected')) {
      startSession();
    }
  }, [searchParams, status, startSession]);

  const handleMicClick = () => {
    if (status === 'idle' || status === 'disconnected' || status === 'error') {
      startSession();
    } else if (status === 'listening' || status === 'connected') {
      // Already listening
    } else if (status === 'speaking') {
      interrupt();
    }
  };

  const handleStopSpeaking = () => {
    interrupt();
  };

  const handleRepeat = () => {
    repeatLastAnswer();
  };

  const handleCopyTranscript = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleLanguageChange = (code: LanguageCode) => {
    setLanguage(code);
    if (status !== 'idle' && status !== 'disconnected') {
      endSession();
      setTimeout(() => startSession(), 500);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      if (e.code === 'Space') {
        e.preventDefault();
        handleMicClick();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        endSession();
      } else if (e.key === 'm' || e.key === 'M') {
        e.preventDefault();
        toggleMute();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        handleRepeat();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [status, endSession, toggleMute]);

  const isActive = ['requesting_permission', 'connecting', 'connected', 'listening', 'processing', 'speaking', 'reconnecting'].includes(status);

  return (
    <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden" dir={language.direction}>
      {/* Mobile-only status & quick controls bar (< 1024px) */}
      <div className="lg:hidden flex items-center justify-between px-3 sm:px-4 py-2.5 bg-background-secondary/90 border-b border-border-primary text-body-sm flex-wrap gap-2">
        <ConnectionStatus status={status} compact />
        <div className="flex items-center gap-1.5 sm:gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRepeat}
            disabled={!transcripts.some(t => t.speaker === 'assistant' && t.isFinal)}
            aria-label={t('conversation.repeat')}
          >
            <RotateCcw className="h-4 w-4 mr-1" aria-hidden="true" />
            <span className="text-caption">{t('conversation.repeat')}</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleMute}
            aria-label={isMuted ? 'Unmute microphone' : 'Mute microphone'}
          >
            {isMuted ? (
              <VolumeX className="h-4 w-4 text-error-primary mr-1" aria-hidden="true" />
            ) : (
              <Volume2 className="h-4 w-4 mr-1" aria-hidden="true" />
            )}
            <span className="text-caption">{isMuted ? 'Unmute' : 'Mute'}</span>
          </Button>
          {isActive && (
            <Button
              variant="danger"
              size="sm"
              onClick={endSession}
              aria-label={t('conversation.end')}
            >
              <X className="h-4 w-4 mr-1" aria-hidden="true" />
              <span className="text-caption">{t('conversation.end')}</span>
            </Button>
          )}
        </div>
      </div>

      {/* Dual Pane Layout */}
      <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
        {/* Conversation & Transcript Pane */}
        <div className="flex-1 flex flex-col min-w-0 border-r border-border-primary min-h-0">
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="p-3 sm:p-4 lg:p-8 flex-1 overflow-y-auto">
              <Transcript
                messages={transcripts}
                currentUserText={currentUserTranscript}
                currentAssistantText={currentAssistantTranscript}
                onRepeat={handleRepeat}
                onCopy={handleCopyTranscript}
                className="h-full"
              />
              <div ref={transcriptEndRef} aria-hidden="true" />
            </div>

            {error && (
              <div className="p-3 sm:p-4 lg:p-6 bg-error-muted border-t border-error-muted animate-slide-down" role="alert">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 p-2 bg-error-secondary/20 rounded-lg text-error-primary">
                    <X className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-body text-error-primary">{t('error.api')}</p>
                    <p className="text-body-sm text-foreground-secondary mt-1">{error}</p>
                    <div className="flex gap-2 mt-3">
                      <Button variant="primary" size="sm" onClick={startSession}>
                        <Loader2 className="h-4 w-4 mr-2" aria-hidden="true" />
                        Try Again
                      </Button>
                      <Button variant="ghost" size="sm" onClick={clearError}>
                        Dismiss
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Bottom Audio Controls */}
            <div className="p-4 sm:p-6 bg-background-secondary border-t border-border-primary">
              <MicrophoneButton
                ref={micButtonRef}
                status={status}
                isMuted={isMuted}
                onClick={handleMicClick}
                onStopSpeaking={handleStopSpeaking}
                onToggleMute={toggleMute}
                size="2xl"
                disabled={status === 'requesting_permission' || status === 'connecting' || status === 'reconnecting'}
              />
            </div>
          </div>
        </div>

        {/* Desktop Sidebar (>= 1024px) */}
        <aside className="hidden lg:flex w-80 bg-background-secondary border-l border-border-primary flex-col min-h-0 overflow-hidden">
          <div className="p-6 border-b border-border-primary">
            <h2 className="text-h4 font-semibold text-foreground-primary mb-4">Session Info</h2>
            <ConnectionStatusDetailed status={status} sessionId={sessionId} />
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div>
              <h3 className="font-medium text-body-sm text-foreground-secondary mb-3">Current Language</h3>
              <LanguageSelector variant="pills" onChange={handleLanguageChange} />
            </div>

            <div>
              <h3 className="font-medium text-body-sm text-foreground-secondary mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <Button variant="secondary" fullWidth onClick={handleRepeat} disabled={!transcripts.some(t => t.speaker === 'assistant' && t.isFinal)}>
                  <RotateCcw className="h-4 w-4 mr-2" aria-hidden="true" />
                  {t('conversation.repeat')}
                </Button>
                <Button variant="secondary" fullWidth onClick={toggleMute}>
                  {isMuted ? (
                    <>
                      <VolumeX className="h-4 w-4 mr-2" aria-hidden="true" />
                      Unmute
                    </>
                  ) : (
                    <>
                      <Volume2 className="h-4 w-4 mr-2" aria-hidden="true" />
                      Mute
                    </>
                  )}
                </Button>
                {isActive && (
                  <Button variant="danger" fullWidth onClick={endSession}>
                    <X className="h-4 w-4 mr-2" aria-hidden="true" />
                    {t('conversation.end')}
                  </Button>
                )}
              </div>
            </div>

            <div>
              <h3 className="font-medium text-body-sm text-foreground-secondary mb-3">Accessibility</h3>
              <AccessibilitySettings compact />
            </div>

            <div className="pt-4 border-t border-border-primary">
              <p className="text-caption text-foreground-muted text-center">
                Press the microphone button to start speaking.
                {status === 'listening' && ' I\'m listening...'}
                {status === 'speaking' && ' Assistant is speaking...'}
              </p>
            </div>
          </div>
        </aside>
      </div>

      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 animate-fade-in">
          <div className="w-full max-w-md bg-background-primary rounded-xl shadow-strong p-6 animate-scale-in">
            <h2 className="text-h4 font-semibold text-foreground-primary mb-4">Settings</h2>
            <div className="space-y-4">
              <LanguageSelector variant="pills" onChange={handleLanguageChange} />
              <AccessibilitySettings />
              {isAuthenticated ? (
                <Button variant="danger" fullWidth onClick={logout}>
                  <LogOut className="h-4 w-4 mr-2" aria-hidden="true" />
                  Sign Out
                </Button>
              ) : (
                <Button
                  variant="primary"
                  fullWidth
                  onClick={() => {
                    setShowSettings(false);
                    login();
                  }}
                >
                  Sign In with Google
                </Button>
              )}
            </div>
            <Button variant="ghost" fullWidth className="mt-4" onClick={() => setShowSettings(false)}>
              Close
            </Button>
          </div>
        </div>
      )}

      {showAccessibility && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/50 animate-fade-in">
          <div className="w-full max-w-md max-h-[90vh] overflow-y-auto bg-background-primary rounded-t-2xl sm:rounded-xl shadow-strong animate-slide-up">
            <div className="sticky top-0 bg-background-primary border-b border-border-primary p-4 flex items-center justify-between">
              <h2 className="text-h4 font-semibold text-foreground-primary">{t('settings.accessibility')}</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowAccessibility(false)} aria-label="Close">
                <X className="h-5 w-5" />
              </Button>
            </div>
            <div className="p-4">
              <AccessibilitySettings />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
