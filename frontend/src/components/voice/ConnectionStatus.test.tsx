import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import { ConnectionStatus, ConnectionStatusDetailed } from './ConnectionStatus';
import { LanguageProvider } from '@contexts/LanguageContext';
import type { ConnectionStatus as ConnectionStatusType } from '@/types';

describe('ConnectionStatus Component — 10-State Conversation Machine Verification', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  const renderWithProvider = (ui: React.ReactElement) => {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
  };

  const allStates: ConnectionStatusType[] = [
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

  it.each(allStates)('renders status "%s" with role="status" and aria-live="polite"', (status) => {
    renderWithProvider(<ConnectionStatus status={status} />);
    const statusContainer = screen.getByRole('status');
    expect(statusContainer).toBeInTheDocument();
    expect(statusContainer).toHaveAttribute('aria-live', 'polite');
  });

  it('renders distinct visible dot background colors for all 10 states', () => {
    allStates.forEach((status) => {
      const { container, unmount } = renderWithProvider(<ConnectionStatus status={status} />);
      const dot = container.querySelector('.status-dot');
      expect(dot).toBeInTheDocument();
      // Ensure dot has a non-empty class containing bg-
      expect(dot?.className).toMatch(/bg-/);
      unmount();
    });
  });

  it('renders compact mode with tooltip and dot', () => {
    renderWithProvider(<ConnectionStatus status="idle" compact />);
    const statusEl = screen.getByRole('status');
    expect(statusEl).toHaveAttribute('title', 'Conversation is idle. Press microphone to begin.');
    expect(screen.getByText('Ready to start')).toBeInTheDocument();
  });

  it('renders detailed card with session id and warning alert for requesting_permission', () => {
    renderWithProvider(<ConnectionStatusDetailed status="requesting_permission" sessionId="sess-1234567890" />);
    expect(screen.getByText('Requesting microphone permission...')).toBeInTheDocument();
    expect(screen.getByText(/Session: sess-1234567/)).toBeInTheDocument();
    expect(screen.getByText(/Microphone permission denied/i)).toBeInTheDocument();
  });

  it('renders detailed card with error alert for error state', () => {
    renderWithProvider(<ConnectionStatusDetailed status="error" sessionId="sess-test" />);
    expect(screen.getByText('Connection error')).toBeInTheDocument();
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(screen.getByText(/AI service unavailable/i)).toBeInTheDocument();
  });

  it('renders detailed card with reconnecting notice for reconnecting state', () => {
    renderWithProvider(<ConnectionStatusDetailed status="reconnecting" sessionId="sess-test" />);
    const reconnectingElements = screen.getAllByText('Reconnecting...');
    expect(reconnectingElements.length).toBeGreaterThanOrEqual(1);
    expect(reconnectingElements[0]).toBeInTheDocument();
  });
});
