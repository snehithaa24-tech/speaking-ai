import React from 'react';
import { Copy, RotateCcw } from 'lucide-react';
import { cn } from '@utils/cn';
import { TranscriptMessage } from '@/types';
import { getLanguage } from '@/types';
import { useLanguage } from '@contexts/LanguageContext';
import { useAccessibility } from '@contexts/AccessibilityContext';

interface TranscriptProps {
  messages: TranscriptMessage[];
  currentUserText: string;
  currentAssistantText: string;
  onRepeat?: () => void;
  onCopy?: (text: string) => void;
  className?: string;
}

export function Transcript({
  messages,
  currentUserText,
  currentAssistantText,
  onRepeat,
  onCopy,
  className,
}: TranscriptProps) {
  const { t, languageCode } = useLanguage();
  const { settings: accessibilitySettings } = useAccessibility();

  const allMessages = React.useMemo(() => {
    const msgs = [...messages];
    if (currentUserText) {
      msgs.push({
        id: 'current-user',
        speaker: 'user',
        text: currentUserText,
        language: languageCode,
        timestamp: Date.now(),
        isFinal: false,
      });
    }
    if (currentAssistantText) {
      msgs.push({
        id: 'current-assistant',
        speaker: 'assistant',
        text: currentAssistantText,
        language: languageCode,
        timestamp: Date.now(),
        isFinal: false,
      });
    }
    return msgs;
  }, [messages, currentUserText, currentAssistantText, languageCode]);

  if (allMessages.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center h-full text-foreground-muted', className)}>
        <p className="text-body text-center px-4">
          {t('conversation.startHint')}
        </p>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-3 overflow-y-auto pr-2', className)} role="log" aria-live="polite" aria-label="Conversation transcript">
      {allMessages.map((message) => (
        <TranscriptMessageComponent
          key={message.id}
          message={message}
          isCurrent={message.id.startsWith('current-')}
          onCopy={onCopy}
          onRepeat={onRepeat}
          showActions={message.speaker === 'assistant' && message.isFinal}
          accessibilitySettings={accessibilitySettings}
          languageCode={languageCode}
        />
      ))}
      <div ref={el => el?.scrollIntoView?.()} aria-hidden="true" />
    </div>
  );
}

interface TranscriptMessageComponentProps {
  message: TranscriptMessage;
  isCurrent?: boolean;
  onCopy?: (text: string) => void;
  onRepeat?: () => void;
  showActions?: boolean;
  accessibilitySettings: { largeText: boolean };
  languageCode: string;
}

function TranscriptMessageComponent({ message, isCurrent, onCopy, onRepeat, showActions, accessibilitySettings, languageCode }: TranscriptMessageComponentProps) {
  const { t } = useLanguage();
  const language = getLanguage(message.language);

  const isUser = message.speaker === 'user';

  return (
    <div
      className={cn(
        'transcript-message animate-fade-in',
        isUser && 'transcript-user',
        !isUser && 'transcript-assistant',
        isCurrent && 'opacity-70'
      )}
      dir={language.direction}
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-body-sm font-medium">
        {isUser ? (
          <span className="bg-brand-primary text-white">U</span>
        ) : (
          <span className="bg-brand-muted text-brand-primary">AI</span>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-caption font-medium text-foreground-secondary">
            {isUser ? t('conversation.microphone') : 'Sahayak AI'}
          </span>
          <span className="text-caption text-foreground-muted">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {message.language !== languageCode && (
            <span className="badge badge-primary text-[0.5rem] px-1.5 py-0.5">
              {getLanguage(message.language).nativeName}
            </span>
          )}
        </div>

        <div className="transcript-bubble relative">
          <p
            className={cn(
              'whitespace-pre-wrap break-words',
              accessibilitySettings.largeText && 'text-body-lg',
              !accessibilitySettings.largeText && 'text-body'
            )}
            dir={language.direction}
            lang={message.language}
          >
            {message.text || (isCurrent ? '...' : '')}
          </p>

          {showActions && (
            <div className="flex items-center gap-1 mt-2 pt-2 border-t border-border-primary/50">
              {onCopy && (
                <button
                  type="button"
                  onClick={() => onCopy?.(message.text)}
                  className="btn btn-ghost btn-sm focus-ring p-1.5"
                  aria-label="Copy message"
                >
                  <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              )}
              <button
                type="button"
                onClick={onRepeat}
                className="btn btn-ghost btn-sm focus-ring p-1.5 flex items-center gap-1"
                aria-label="Repeat answer"
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="text-caption">{t('conversation.repeat')}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}