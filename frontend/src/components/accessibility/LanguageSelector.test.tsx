// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { LanguageSelector } from './LanguageSelector';
import { LanguageProvider } from '@contexts/LanguageContext';

describe('LanguageSelector Component — Milestone 2 Verification', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = '';
    document.documentElement.className = '';
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  const renderWithProvider = (ui: React.ReactElement) => {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
  };

  it('renders strictly two language options: English and हिन्दी', () => {
    renderWithProvider(<LanguageSelector variant="pills" />);
    const radioButtons = screen.getAllByRole('radio');
    expect(radioButtons).toHaveLength(2);
    expect(screen.getByText('English')).toBeInTheDocument();
    expect(screen.getByText('हिन्दी')).toBeInTheDocument();
  });

  it('contains zero Telugu references or options', () => {
    renderWithProvider(<LanguageSelector variant="pills" />);
    expect(screen.queryByText(/telugu/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/తెలుగు/)).not.toBeInTheDocument();
    expect(screen.queryByText(/te-IN/i)).not.toBeInTheDocument();
  });

  it('displays the exact text and separator "English | हिन्दी"', () => {
    const { container } = renderWithProvider(<LanguageSelector />);
    expect(container.textContent).toContain('English');
    expect(container.textContent).toContain('|');
    expect(container.textContent).toContain('हिन्दी');
  });

  it('does NOT render a third option under any variant (pills or grid)', () => {
    const { unmount } = renderWithProvider(<LanguageSelector variant="grid" />);
    const gridRadios = screen.getAllByRole('radio');
    expect(gridRadios).toHaveLength(2);
    unmount();

    renderWithProvider(<LanguageSelector variant="pills" />);
    const pillRadios = screen.getAllByRole('radio');
    expect(pillRadios).toHaveLength(2);
  });

  it('defaults to English (en-IN) as active', () => {
    renderWithProvider(<LanguageSelector variant="pills" />);
    const englishBtn = screen.getByRole('radio', { name: 'English' });
    const hindiBtn = screen.getByRole('radio', { name: 'हिन्दी' });

    expect(englishBtn).toHaveAttribute('aria-checked', 'true');
    expect(hindiBtn).toHaveAttribute('aria-checked', 'false');
    expect(document.documentElement.lang).toBe('en-IN');
  });

  it('switches to Hindi when clicked and persists to localStorage', () => {
    renderWithProvider(<LanguageSelector variant="pills" />);
    const hindiBtn = screen.getByRole('radio', { name: 'हिन्दी' });
    const englishBtn = screen.getByRole('radio', { name: 'English' });

    fireEvent.click(hindiBtn);

    expect(hindiBtn).toHaveAttribute('aria-checked', 'true');
    expect(englishBtn).toHaveAttribute('aria-checked', 'false');
    expect(localStorage.getItem('sahayak-language')).toBe('hi-IN');
    expect(document.documentElement.lang).toBe('hi-IN');
  });

  it('switches back to English when English button is clicked', () => {
    localStorage.setItem('sahayak-language', 'hi-IN');
    renderWithProvider(<LanguageSelector variant="pills" />);

    const englishBtn = screen.getByRole('radio', { name: 'English' });
    const hindiBtn = screen.getByRole('radio', { name: 'हिन्दी' });

    expect(hindiBtn).toHaveAttribute('aria-checked', 'true');

    fireEvent.click(englishBtn);

    expect(englishBtn).toHaveAttribute('aria-checked', 'true');
    expect(hindiBtn).toHaveAttribute('aria-checked', 'false');
    expect(localStorage.getItem('sahayak-language')).toBe('en-IN');
    expect(document.documentElement.lang).toBe('en-IN');
  });

  it('calls onChange prop when selection changes', () => {
    const onChange = vi.fn();
    renderWithProvider(<LanguageSelector onChange={onChange} />);

    fireEvent.click(screen.getByRole('radio', { name: 'हिन्दी' }));
    expect(onChange).toHaveBeenCalledWith('hi-IN');

    fireEvent.click(screen.getByRole('radio', { name: 'English' }));
    expect(onChange).toHaveBeenCalledWith('en-IN');
  });

  it('supports keyboard navigation via Arrow keys', () => {
    renderWithProvider(<LanguageSelector />);
    const englishBtn = screen.getByRole('radio', { name: 'English' });
    const hindiBtn = screen.getByRole('radio', { name: 'हिन्दी' });

    englishBtn.focus();
    fireEvent.keyDown(englishBtn, { key: 'ArrowRight' });

    expect(hindiBtn).toHaveAttribute('aria-checked', 'true');
    expect(englishBtn).toHaveAttribute('aria-checked', 'false');

    fireEvent.keyDown(hindiBtn, { key: 'ArrowLeft' });

    expect(englishBtn).toHaveAttribute('aria-checked', 'true');
    expect(hindiBtn).toHaveAttribute('aria-checked', 'false');
  });

  it('gracefully discards legacy te-IN from localStorage and defaults to English', () => {
    localStorage.setItem('sahayak-language', 'te-IN');
    renderWithProvider(<LanguageSelector />);

    const englishBtn = screen.getByRole('radio', { name: 'English' });
    expect(englishBtn).toHaveAttribute('aria-checked', 'true');
    expect(screen.queryByText(/telugu/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/తెలుగు/)).not.toBeInTheDocument();
  });

  it('renders correctly in grid variant for settings page with two options', () => {
    renderWithProvider(<LanguageSelector variant="grid" />);
    const radioButtons = screen.getAllByRole('radio');
    expect(radioButtons).toHaveLength(2);
    expect(screen.getByText('English')).toBeInTheDocument();
    expect(screen.getByText('हिन्दी')).toBeInTheDocument();
    expect(screen.queryByText(/telugu/i)).not.toBeInTheDocument();
  });
});
