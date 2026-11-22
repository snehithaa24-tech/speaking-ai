import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface AccessibilitySettings {
  largeText: boolean;
  highContrast: boolean;
  reducedMotion: boolean;
  volume: number;
  screenReaderOptimized: boolean;
  keyboardNavigation: boolean;
}

interface AccessibilityContextType {
  settings: AccessibilitySettings;
  toggleLargeText: () => void;
  toggleHighContrast: () => void;
  toggleReducedMotion: () => void;
  setVolume: (volume: number) => void;
  toggleScreenReaderOptimized: () => void;
  toggleKeyboardNavigation: () => void;
  resetToDefaults: () => void;
}

const defaultSettings: AccessibilitySettings = {
  largeText: false,
  highContrast: false,
  reducedMotion: false,
  volume: 1,
  screenReaderOptimized: true,
  keyboardNavigation: true,
};

const AccessibilityContext = createContext<AccessibilityContextType | null>(null);

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<AccessibilitySettings>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('sahayak-accessibility');
      if (stored) {
        try {
          return { ...defaultSettings, ...JSON.parse(stored) };
        } catch {
          return defaultSettings;
        }
      }
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const prefersHighContrast = window.matchMedia('(prefers-contrast: high)').matches;
      return {
        ...defaultSettings,
        reducedMotion: prefersReducedMotion,
        highContrast: prefersHighContrast,
      };
    }
    return defaultSettings;
  });

  useEffect(() => {
    localStorage.setItem('sahayak-accessibility', JSON.stringify(settings));

    const root = document.documentElement;
    if (settings.largeText) root.classList.add('large-text');
    else root.classList.remove('large-text');

    if (settings.highContrast) root.classList.add('high-contrast');
    else root.classList.remove('high-contrast');

    if (settings.reducedMotion) root.classList.add('reduced-motion');
    else root.classList.remove('reduced-motion');
  }, [settings]);

  const updateSetting = useCallback(<K extends keyof AccessibilitySettings>(
    key: K,
    value: AccessibilitySettings[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  }, []);

  const toggleLargeText = useCallback(() => {
    updateSetting('largeText', !settings.largeText);
  }, [settings.largeText, updateSetting]);

  const toggleHighContrast = useCallback(() => {
    updateSetting('highContrast', !settings.highContrast);
  }, [settings.highContrast, updateSetting]);

  const toggleReducedMotion = useCallback(() => {
    updateSetting('reducedMotion', !settings.reducedMotion);
  }, [settings.reducedMotion, updateSetting]);

  const setVolume = useCallback((volume: number) => {
    updateSetting('volume', Math.max(0, Math.min(1, volume)));
  }, [updateSetting]);

  const toggleScreenReaderOptimized = useCallback(() => {
    updateSetting('screenReaderOptimized', !settings.screenReaderOptimized);
  }, [settings.screenReaderOptimized, updateSetting]);

  const toggleKeyboardNavigation = useCallback(() => {
    updateSetting('keyboardNavigation', !settings.keyboardNavigation);
  }, [settings.keyboardNavigation, updateSetting]);

  const resetToDefaults = useCallback(() => {
    setSettings(defaultSettings);
  }, []);

  return (
    <AccessibilityContext.Provider
      value={{
        settings,
        toggleLargeText,
        toggleHighContrast,
        toggleReducedMotion,
        setVolume,
        toggleScreenReaderOptimized,
        toggleKeyboardNavigation,
        resetToDefaults,
      }}
    >
      {children}
    </AccessibilityContext.Provider>
  );
}

export function useAccessibility(): AccessibilityContextType {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  return context;
}