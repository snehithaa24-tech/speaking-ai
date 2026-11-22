import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '@/App';
import { Conversation } from '@/pages/Conversation';
import { LanguageProvider } from '@/contexts/LanguageContext';
import { AccessibilityProvider } from '@/contexts/AccessibilityContext';
import { AuthProvider } from '@/contexts/AuthContext';
import { ErrorBoundary } from '@/components/ErrorBoundary';

describe('App and Conversation Smoke Test', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  it('renders App at /conversation?category=government without crashing', () => {
    const { container } = render(
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/conversation?category=government']}>
            <AuthProvider>
              <LanguageProvider>
                <AccessibilityProvider>
                  <App />
                </AccessibilityProvider>
              </LanguageProvider>
            </AuthProvider>
          </MemoryRouter>
        </QueryClientProvider>
      </ErrorBoundary>
    );

    expect(container).toBeDefined();
    expect(container.innerHTML).not.toBe('');
    expect(container.querySelector('header')).not.toBeNull();
  });

  it('renders Conversation directly without crashing', () => {
    const { container } = render(
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/conversation?category=government']}>
            <AuthProvider>
              <LanguageProvider>
                <AccessibilityProvider>
                  <Conversation />
                </AccessibilityProvider>
              </LanguageProvider>
            </AuthProvider>
          </MemoryRouter>
        </QueryClientProvider>
      </ErrorBoundary>
    );

    expect(container).toBeDefined();
    expect(container.innerHTML).not.toBe('');
  });
});
