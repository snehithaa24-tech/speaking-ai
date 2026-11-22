import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { MicrophoneButton } from './MicrophoneButton';
import type { ConnectionStatus } from '@/types';

describe('MicrophoneButton Component — 10-State Machine & Controls Verification', () => {
  beforeEach(() => {
    cleanup();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const allStates: ConnectionStatus[] = [
    'idle',
    'requesting_permission',
    'connecting',
    'connected',
    'listening',
    'processing',
    'speaking',
    'reconnecting',
    'disconnected',
    'error',
  ];

  it.each(allStates)('renders button for state "%s" without crashing', (status) => {
    render(<MicrophoneButton status={status} isMuted={false} onClick={vi.fn()} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThanOrEqual(1);
  });

  it('disables main button during busy transition states', () => {
    const busyStates: ConnectionStatus[] = ['requesting_permission', 'connecting', 'reconnecting'];

    busyStates.forEach((status) => {
      const { unmount } = render(
        <MicrophoneButton status={status} isMuted={false} onClick={vi.fn()} />
      );
      const mainBtn = screen.getAllByRole('button')[0];
      expect(mainBtn).toBeDisabled();
      expect(mainBtn).toHaveAttribute('aria-busy', 'true');
      unmount();
    });
  });

  it('sets aria-pressed="true" during active conversation states', () => {
    const activeStates: ConnectionStatus[] = ['connected', 'listening', 'processing', 'speaking'];

    activeStates.forEach((status) => {
      const { unmount } = render(
        <MicrophoneButton status={status} isMuted={false} onClick={vi.fn()} />
      );
      const mainBtn = screen.getAllByRole('button')[0];
      expect(mainBtn).toHaveAttribute('aria-pressed', 'true');
      unmount();
    });
  });

  it('invokes onClick callback when clicked in ready state', () => {
    const onClick = vi.fn();
    render(<MicrophoneButton status="idle" isMuted={false} onClick={onClick} />);
    const mainBtn = screen.getAllByRole('button')[0];
    fireEvent.click(mainBtn);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('renders Stop Speaking button when speaking and calls onStopSpeaking', () => {
    const onStop = vi.fn();
    render(
      <MicrophoneButton
        status="speaking"
        isMuted={false}
        onClick={vi.fn()}
        onStopSpeaking={onStop}
      />
    );
    const stopBtn = screen.getByRole('button', { name: /stop assistant from speaking/i });
    expect(stopBtn).toBeInTheDocument();

    fireEvent.click(stopBtn);
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it('renders mute button and calls onToggleMute on click', () => {
    const onToggleMute = vi.fn();
    const { rerender } = render(
      <MicrophoneButton
        status="listening"
        isMuted={false}
        onClick={vi.fn()}
        onToggleMute={onToggleMute}
      />
    );

    const muteBtn = screen.getByRole('button', { name: /mute microphone/i });
    expect(muteBtn).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(muteBtn);
    expect(onToggleMute).toHaveBeenCalledTimes(1);

    // Re-render as muted
    rerender(
      <MicrophoneButton
        status="listening"
        isMuted={true}
        onClick={vi.fn()}
        onToggleMute={onToggleMute}
      />
    );

    const unmuteBtn = screen.getByRole('button', { name: /unmute microphone/i });
    expect(unmuteBtn).toHaveAttribute('aria-pressed', 'true');
  });
});
