import React, { forwardRef } from 'react';
import { Mic, Loader2, X, Volume2, VolumeX } from 'lucide-react';
import { cn } from '@utils/cn';
import type { ConnectionStatus } from '@/types';

export interface MicrophoneButtonProps {
  status: ConnectionStatus;
  isMuted: boolean;
  onClick: () => void;
  onStopSpeaking?: () => void;
  onToggleMute?: () => void;
  size?: 'lg' | 'xl' | '2xl';
  disabled?: boolean;
  ariaLabel?: string;
}

const statusConfig: Record<ConnectionStatus, { className: string; icon: React.ReactNode; label: string; ariaLabel: string }> = {
  idle: {
    className: 'mic-button-idle',
    icon: <Mic className="h-8 w-8" aria-hidden="true" />,
    label: 'Start conversation',
    ariaLabel: 'Start voice conversation',
  },
  requesting_permission: {
    className: 'mic-button-processing',
    icon: <Loader2 className="h-8 w-8 animate-spin-slow" aria-hidden="true" />,
    label: 'Requesting permission...',
    ariaLabel: 'Requesting microphone permission',
  },
  connecting: {
    className: 'mic-button-processing',
    icon: <Loader2 className="h-8 w-8 animate-spin-slow" aria-hidden="true" />,
    label: 'Connecting...',
    ariaLabel: 'Connecting to voice service',
  },
  connected: {
    className: 'mic-button-idle',
    icon: <Mic className="h-8 w-8" aria-hidden="true" />,
    label: 'Connected',
    ariaLabel: 'Connected. Ready to listen',
  },
  listening: {
    className: 'mic-button-listening',
    icon: <Mic className="h-8 w-8" aria-hidden="true" />,
    label: 'Listening...',
    ariaLabel: 'Listening to your speech',
  },
  processing: {
    className: 'mic-button-processing',
    icon: <Loader2 className="h-8 w-8 animate-spin-slow" aria-hidden="true" />,
    label: 'Processing...',
    ariaLabel: 'Processing response',
  },
  speaking: {
    className: 'mic-button-speaking',
    icon: <Volume2 className="h-8 w-8" aria-hidden="true" />,
    label: 'Speaking...',
    ariaLabel: 'Assistant is speaking. Click to interrupt',
  },
  reconnecting: {
    className: 'mic-button-processing',
    icon: <Loader2 className="h-8 w-8 animate-spin-slow" aria-hidden="true" />,
    label: 'Reconnecting...',
    ariaLabel: 'Reconnecting to voice service',
  },
  disconnected: {
    className: 'mic-button-idle',
    icon: <Mic className="h-8 w-8" aria-hidden="true" />,
    label: 'Start conversation',
    ariaLabel: 'Start conversation',
  },
  error: {
    className: 'mic-button-error',
    icon: <X className="h-8 w-8" aria-hidden="true" />,
    label: 'Error, try again',
    ariaLabel: 'Connection error. Click to try again',
  },
};

const sizeClasses = {
  lg: 'w-16 h-16',
  xl: 'w-20 h-20',
  '2xl': 'w-24 h-24',
};

export const MicrophoneButton = forwardRef<HTMLButtonElement, MicrophoneButtonProps>(
  (
    {
      status,
      isMuted,
      onClick,
      onStopSpeaking,
      onToggleMute,
      size = '2xl',
      disabled,
      ariaLabel,
    },
    ref
  ) => {
    const config = statusConfig[status] || statusConfig.idle;
    const isActive = ['connected', 'listening', 'processing', 'speaking'].includes(status);
    const isBusy = status === 'requesting_permission' || status === 'connecting' || status === 'processing' || status === 'reconnecting';
    const isButtonDisabled = disabled || status === 'requesting_permission' || status === 'connecting' || status === 'reconnecting';
    const showStopButton = status === 'speaking' && Boolean(onStopSpeaking);

    return (
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <button
            ref={ref}
            type="button"
            className={cn(
              'mic-button',
              config.className,
              sizeClasses[size],
              isButtonDisabled && 'opacity-50 cursor-not-allowed',
              isActive && 'ring-4 ring-brand-primary/20'
            )}
            onClick={onClick}
            disabled={isButtonDisabled}
            aria-label={ariaLabel || config.ariaLabel}
            aria-pressed={isActive}
            aria-busy={isBusy}
          >
            {config.icon}
          </button>

          {status === 'listening' && (
            <span className="sr-only" aria-live="polite">
              Listening to your speech
            </span>
          )}

          {status === 'speaking' && (
            <span className="sr-only" aria-live="polite">
              Assistant is speaking
            </span>
          )}
        </div>

        {showStopButton && (
          <button
            type="button"
            onClick={onStopSpeaking}
            className="btn btn-danger btn-sm focus-ring"
            aria-label="Stop assistant from speaking"
          >
            <X className="h-4 w-4 mr-2" aria-hidden="true" />
            Stop Speaking
          </button>
        )}

        <div className="flex items-center gap-3 text-body-sm text-foreground-secondary">
          <button
            type="button"
            onClick={onToggleMute}
            disabled={disabled || status === 'disconnected' || status === 'idle'}
            className="btn btn-ghost btn-sm focus-ring"
            aria-label={isMuted ? 'Unmute microphone' : 'Mute microphone'}
            aria-pressed={isMuted}
          >
            {isMuted ? (
              <VolumeX className="h-4 w-4 text-error-primary" aria-hidden="true" />
            ) : (
              <Volume2 className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
          <span className="font-medium">{config.label}</span>
        </div>
      </div>
    );
  }
);

MicrophoneButton.displayName = 'MicrophoneButton';
