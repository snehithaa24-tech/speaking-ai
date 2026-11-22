import React from 'react';
import { WifiOff, Loader2, CheckCircle, XCircle, Mic, CircleDot, Volume2 } from 'lucide-react';
import { cn } from '@utils/cn';
import type { ConnectionStatus as ConnectionStatusType } from '@/types';
import { useLanguage } from '@contexts/LanguageContext';

const statusConfig: Record<ConnectionStatusType, {
  label: string;
  icon: React.ReactNode;
  variant: 'primary' | 'success' | 'warning' | 'error' | 'neutral';
  dotColor: string;
  tooltip: string;
}> = {
  idle: {
    label: 'Ready to start',
    icon: <CircleDot className="h-4 w-4" aria-hidden="true" />,
    variant: 'neutral',
    dotColor: 'bg-foreground-muted',
    tooltip: 'Conversation is idle. Press microphone to begin.',
  },
  requesting_permission: {
    label: 'Requesting permission...',
    icon: <Loader2 className="h-4 w-4 animate-spin-slow" aria-hidden="true" />,
    variant: 'warning',
    dotColor: 'bg-warning-secondary animate-pulse-soft',
    tooltip: 'Requesting microphone permission from your browser...',
  },
  connecting: {
    label: 'Connecting...',
    icon: <Loader2 className="h-4 w-4 animate-spin-slow" aria-hidden="true" />,
    variant: 'primary',
    dotColor: 'bg-brand-secondary animate-pulse-soft',
    tooltip: 'Connecting to SAHAYAK AI voice service...',
  },
  connected: {
    label: 'Connected',
    icon: <CheckCircle className="h-4 w-4" aria-hidden="true" />,
    variant: 'success',
    dotColor: 'bg-success-secondary',
    tooltip: 'Connected and ready.',
  },
  listening: {
    label: 'Listening...',
    icon: <Mic className="h-4 w-4" aria-hidden="true" />,
    variant: 'primary',
    dotColor: 'bg-brand-primary animate-pulse-soft',
    tooltip: 'Listening to your speech...',
  },
  processing: {
    label: 'Processing...',
    icon: <Loader2 className="h-4 w-4 animate-spin-slow" aria-hidden="true" />,
    variant: 'primary',
    dotColor: 'bg-accent-secondary animate-pulse-soft',
    tooltip: 'Processing your request...',
  },
  speaking: {
    label: 'Speaking...',
    icon: <Volume2 className="h-4 w-4" aria-hidden="true" />,
    variant: 'success',
    dotColor: 'bg-success-primary animate-pulse-soft',
    tooltip: 'Assistant is speaking...',
  },
  reconnecting: {
    label: 'Reconnecting...',
    icon: <Loader2 className="h-4 w-4 animate-spin-slow" aria-hidden="true" />,
    variant: 'warning',
    dotColor: 'bg-warning-primary animate-pulse-soft',
    tooltip: 'Connection lost. Reconnecting...',
  },
  disconnected: {
    label: 'Disconnected',
    icon: <WifiOff className="h-4 w-4" aria-hidden="true" />,
    variant: 'neutral',
    dotColor: 'bg-foreground-muted',
    tooltip: 'Disconnected from voice service.',
  },
  error: {
    label: 'Error',
    icon: <XCircle className="h-4 w-4" aria-hidden="true" />,
    variant: 'error',
    dotColor: 'bg-error-primary',
    tooltip: 'A connection error occurred.',
  },
};

interface ConnectionStatusProps {
  status: ConnectionStatusType;
  className?: string;
  showLabel?: boolean;
  compact?: boolean;
}

export function ConnectionStatus({ status, className, showLabel = true, compact = false }: ConnectionStatusProps) {
  const { t } = useLanguage();
  const config = statusConfig[status] || statusConfig.idle;
  const translatedLabel = t(`conversation.${status}`) || config.label;

  if (compact) {
    return (
      <span
        className={cn('inline-flex items-center gap-1.5', className)}
        title={config.tooltip}
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <span className={cn('status-dot inline-block', config.dotColor)} aria-hidden="true" />
        {showLabel && <span className="text-body-sm font-medium text-foreground-secondary">{translatedLabel}</span>}
      </span>
    );
  }

  return (
    <div
      className={cn('status-indicator', className)}
      title={config.tooltip}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <span className={cn('status-dot inline-block', config.dotColor)} aria-hidden="true" />
      <span className={cn('font-medium', 'text-foreground-secondary')}>{translatedLabel}</span>
    </div>
  );
}

interface ConnectionStatusDetailedProps {
  status: ConnectionStatusType;
  sessionId?: string | null;
  className?: string;
}

export function ConnectionStatusDetailed({ status, sessionId, className }: ConnectionStatusDetailedProps) {
  const { t } = useLanguage();
  const config = statusConfig[status] || statusConfig.idle;
  const translatedLabel = t(`conversation.${status}`) || config.label;

  const variantClasses = {
    primary: 'bg-brand-muted text-brand-primary border-border-primary',
    success: 'bg-success-muted text-success-primary border-success-muted',
    warning: 'bg-warning-muted text-warning-primary border-warning-muted',
    error: 'bg-error-muted text-error-primary border-error-muted',
    neutral: 'bg-background-tertiary text-foreground-secondary border-border-primary',
  };

  return (
    <div className={cn('card p-4', className)} role="region" aria-label="Connection Status">
      <div className="flex items-center gap-3">
        <div className={cn('p-2 rounded-lg border', variantClasses[config.variant])}>
          {config.icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-h4 font-semibold text-foreground-primary">{translatedLabel}</p>
          <p className="text-body-sm text-foreground-muted mt-0.5">
            {sessionId ? `Session: ${sessionId.slice(0, 12)}...` : 'No active session'}
          </p>
        </div>
      </div>

      {status === 'requesting_permission' && (
        <div className="mt-4 p-3 bg-warning-muted border border-warning-muted rounded-lg" role="status">
          <p className="text-body-sm text-warning-primary">
            {t('error.micPermission') || 'Please allow microphone access in your browser.'}
          </p>
        </div>
      )}

      {status === 'error' && (
        <div className="mt-4 p-3 bg-error-muted border border-error-muted rounded-lg" role="alert">
          <p className="text-body-sm text-error-primary">
            {t('error.api')}
          </p>
        </div>
      )}

      {status === 'reconnecting' && (
        <div className="mt-4 p-3 bg-warning-muted border border-warning-muted rounded-lg" role="status">
          <p className="text-body-sm text-warning-primary">
            {t('conversation.reconnecting') || 'Attempting to reconnect...'}
          </p>
        </div>
      )}
    </div>
  );
}
