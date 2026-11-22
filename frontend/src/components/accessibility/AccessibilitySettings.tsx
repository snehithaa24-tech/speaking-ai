import { Text, Contrast, Move, Volume2, Eye, Keyboard, RefreshCw } from 'lucide-react';
import { cn } from '@utils/cn';
import { useLanguage } from '@contexts/LanguageContext';
import { useAccessibility } from '@contexts/AccessibilityContext';
import { Button } from '@components/shared/Button';

interface AccessibilitySettingsProps {
  className?: string;
  compact?: boolean;
}

export function AccessibilitySettings({ className, compact = false }: AccessibilitySettingsProps) {
  const { t } = useLanguage();
  const {
    settings,
    toggleLargeText,
    toggleHighContrast,
    toggleReducedMotion,
    toggleScreenReaderOptimized,
    toggleKeyboardNavigation,
    setVolume,
    resetToDefaults,
  } = useAccessibility();

  const toggles = [
    {
      key: 'largeText',
      label: t('settings.largeText'),
      description: 'Increase text size for better readability',
      icon: Text,
      onToggle: toggleLargeText,
      enabled: settings.largeText,
    },
    {
      key: 'highContrast',
      label: t('settings.highContrast'),
      description: 'High contrast colors for better visibility',
      icon: Contrast,
      onToggle: toggleHighContrast,
      enabled: settings.highContrast,
    },
    {
      key: 'reducedMotion',
      label: t('settings.reducedMotion'),
      description: 'Reduce animations and transitions',
      icon: Move,
      onToggle: toggleReducedMotion,
      enabled: settings.reducedMotion,
    },
    {
      key: 'screenReaderOptimized',
      label: t('accessibility.screenReader'),
      description: 'Optimize for screen readers',
      icon: Eye,
      onToggle: toggleScreenReaderOptimized,
      enabled: settings.screenReaderOptimized,
    },
    {
      key: 'keyboardNavigation',
      label: t('accessibility.keyboardNav'),
      description: 'Enable keyboard navigation',
      icon: Keyboard,
      onToggle: toggleKeyboardNavigation,
      enabled: settings.keyboardNavigation,
    },
  ];

  if (compact) {
    return (
      <div className={cn('flex flex-wrap items-center gap-4', className)}>
        <div className="flex items-center gap-2">
          <label className="text-body-sm text-foreground-secondary">{t('settings.volume')}</label>
          <input
            type="range"
            min="0"
            max="100"
            value={Math.round(settings.volume * 100)}
            onChange={(e) => setVolume(Number(e.target.value) / 100)}
            className="w-32 h-2 accent-brand-primary"
            aria-label={t('settings.volume')}
          />
          <span className="text-body-sm text-foreground-muted w-10 text-right">{Math.round(settings.volume * 100)}%</span>
        </div>
        <Button variant="ghost" size="sm" onClick={resetToDefaults} aria-label={t('settings.help')}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">{t('settings.help')}</span>
        </Button>
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      <div className="flex items-center justify-between">
        <h2 className="text-h4 font-semibold text-foreground-primary">{t('settings.accessibility')}</h2>
        <Button variant="ghost" size="sm" onClick={resetToDefaults}>
          <RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
          Reset to defaults
        </Button>
      </div>

      <div className="space-y-4" role="group" aria-labelledby="accessibility-heading">
        {toggles.map(({ key, label, description, icon: Icon, onToggle, enabled }) => (
          <div key={key} className="flex items-center justify-between p-4 bg-background-secondary rounded-xl">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-background-primary rounded-lg text-foreground-secondary">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="font-medium text-body text-foreground-primary">{label}</p>
                <p className="text-body-sm text-foreground-muted">{description}</p>
              </div>
            </div>
            <AccessibilityToggle
              checked={enabled}
              onChange={onToggle}
              aria-label={label}
            />
          </div>
        ))}
      </div>

      <div className="pt-4 border-t border-border-primary">
        <label className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-background-primary rounded-lg text-foreground-secondary">
              <Volume2 className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="font-medium text-body text-foreground-primary">{t('settings.volume')}</p>
              <p className="text-body-sm text-foreground-muted">Adjust playback volume</p>
            </div>
          </div>
          <div className="flex-1 max-w-xs flex items-center gap-3">
            <input
              type="range"
              min="0"
              max="100"
              value={Math.round(settings.volume * 100)}
              onChange={(e) => setVolume(Number(e.target.value) / 100)}
              className="flex-1 h-2 accent-brand-primary"
              aria-label={t('settings.volume')}
            />
            <span className="text-body-sm text-foreground-muted w-10 text-right">{Math.round(settings.volume * 100)}%</span>
          </div>
        </label>
      </div>
    </div>
  );
}

interface AccessibilityToggleProps {
  checked: boolean;
  onChange: () => void;
  'aria-label': string;
}

function AccessibilityToggle({ checked, onChange, 'aria-label': ariaLabel }: AccessibilityToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      onClick={onChange}
      className={cn(
        'accessibility-toggle',
        checked ? 'accessibility-toggle-on' : 'accessibility-toggle-off'
      )}
    >
      <span className="accessibility-toggle-thumb" aria-hidden="true" />
    </button>
  );
}