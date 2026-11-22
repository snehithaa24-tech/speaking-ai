import React, { useRef } from 'react';
import { cn } from '@utils/cn';
import { useLanguage } from '@contexts/LanguageContext';
import { LanguageCode } from '@/types';

interface LanguageSelectorProps {
  variant?: 'dropdown' | 'grid' | 'pills' | 'toggle';
  className?: string;
  onChange?: (code: LanguageCode) => void;
}

export function LanguageSelector({
  variant = 'toggle',
  className,
  onChange,
}: LanguageSelectorProps) {
  const { languageCode, setLanguage, t } = useLanguage();
  const englishBtnRef = useRef<HTMLButtonElement>(null);
  const hindiBtnRef = useRef<HTMLButtonElement>(null);

  const handleSelect = (code: LanguageCode) => {
    setLanguage(code);
    onChange?.(code);
  };

  const handleKeyDown = (e: React.KeyboardEvent, currentCode: LanguageCode) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const targetCode: LanguageCode = currentCode === 'en-IN' ? 'hi-IN' : 'en-IN';
      handleSelect(targetCode);
      if (targetCode === 'en-IN') {
        englishBtnRef.current?.focus();
      } else {
        hindiBtnRef.current?.focus();
      }
    }
  };

  if (variant === 'grid') {
    return (
      <div
        className={cn('grid grid-cols-1 sm:grid-cols-2 gap-3', className)}
        role="radiogroup"
        aria-label={t('settings.language')}
      >
        <button
          ref={englishBtnRef}
          type="button"
          role="radio"
          aria-checked={languageCode === 'en-IN'}
          tabIndex={languageCode === 'en-IN' ? 0 : -1}
          onClick={() => handleSelect('en-IN')}
          onKeyDown={(e) => handleKeyDown(e, 'en-IN')}
          className={cn(
            'language-option',
            languageCode === 'en-IN' && 'language-option-selected'
          )}
        >
          <span className="text-xl" aria-hidden="true">🇮🇳</span>
          <div className="flex-1 text-left min-w-0">
            <p className="font-medium text-body text-foreground-primary truncate">English</p>
            <p className="text-caption text-foreground-muted truncate">English (India)</p>
          </div>
          {languageCode === 'en-IN' && (
            <span className="h-5 w-5 rounded-full bg-brand-primary text-white flex items-center justify-center text-caption" aria-hidden="true">✓</span>
          )}
        </button>

        <button
          ref={hindiBtnRef}
          type="button"
          role="radio"
          aria-checked={languageCode === 'hi-IN'}
          tabIndex={languageCode === 'hi-IN' ? 0 : -1}
          onClick={() => handleSelect('hi-IN')}
          onKeyDown={(e) => handleKeyDown(e, 'hi-IN')}
          className={cn(
            'language-option',
            languageCode === 'hi-IN' && 'language-option-selected'
          )}
        >
          <span className="text-xl" aria-hidden="true">🇮🇳</span>
          <div className="flex-1 text-left min-w-0">
            <p className="font-medium text-body text-foreground-primary truncate">हिन्दी</p>
            <p className="text-caption text-foreground-muted truncate">Hindi</p>
          </div>
          {languageCode === 'hi-IN' && (
            <span className="h-5 w-5 rounded-full bg-brand-primary text-white flex items-center justify-center text-caption" aria-hidden="true">✓</span>
          )}
        </button>
      </div>
    );
  }

  // Two-option toggle displaying "English | हिन्दी"
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-xl p-0.5 bg-background-tertiary border border-border-primary text-body-sm select-none',
        className
      )}
      role="radiogroup"
      aria-label={t('settings.language')}
    >
      <button
        ref={englishBtnRef}
        type="button"
        role="radio"
        aria-checked={languageCode === 'en-IN'}
        tabIndex={languageCode === 'en-IN' ? 0 : -1}
        onClick={() => handleSelect('en-IN')}
        onKeyDown={(e) => handleKeyDown(e, 'en-IN')}
        className={cn(
          'px-3 py-1.5 rounded-lg font-medium transition-all duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1',
          languageCode === 'en-IN'
            ? 'bg-brand-primary text-white shadow-soft font-semibold'
            : 'text-foreground-secondary hover:text-foreground-primary hover:bg-background-secondary/60'
        )}
      >
        English
      </button>

      <span className="text-border-secondary px-1 text-caption font-semibold" aria-hidden="true">
        |
      </span>

      <button
        ref={hindiBtnRef}
        type="button"
        role="radio"
        aria-checked={languageCode === 'hi-IN'}
        tabIndex={languageCode === 'hi-IN' ? 0 : -1}
        onClick={() => handleSelect('hi-IN')}
        onKeyDown={(e) => handleKeyDown(e, 'hi-IN')}
        className={cn(
          'px-3 py-1.5 rounded-lg font-medium transition-all duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1',
          languageCode === 'hi-IN'
            ? 'bg-brand-primary text-white shadow-soft font-semibold'
            : 'text-foreground-secondary hover:text-foreground-primary hover:bg-background-secondary/60'
        )}
      >
        हिन्दी
      </button>
    </div>
  );
}
