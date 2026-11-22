import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Language, LanguageCode, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, getLanguage } from '@/types';

interface LanguageContextType {
  currentLanguage: Language;
  languageCode: LanguageCode;
  setLanguage: (code: LanguageCode) => void;
  supportedLanguages: typeof SUPPORTED_LANGUAGES;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<LanguageContextType | null>(null);

const translations: Record<LanguageCode, Record<string, string>> = {
  'en-IN': {
    'app.name': 'SAHAYAK AI',
    'app.tagline': 'Your multilingual voice assistant',
    'nav.home': 'Home',
    'nav.conversation': 'Conversation',
    'home.welcome': 'Welcome to SAHAYAK AI',
    'home.subtitle': 'Press the microphone and speak naturally. I\'ll respond in your language.',
    'home.selectLanguage': 'Select your language',
    'home.startConversation': 'Start Conversation',
    'home.categories.title': 'How can I help you?',
    'home.categories.agriculture': 'Agriculture Assistance',
    'home.categories.agriculture.desc': 'Crop advice, weather, market prices',
    'home.categories.government': 'Government Schemes',
    'home.categories.government.desc': 'Benefits, applications, eligibility',
    'home.categories.transport': 'Transport Information',
    'home.categories.transport.desc': 'Routes, schedules, fares',
    'home.categories.hospital': 'Hospital Assistance',
    'home.categories.hospital.desc': 'Find hospitals, book appointments',
    'home.accessibility': 'Accessibility',
    'home.settings': 'Settings',
    'conversation.idle': 'Ready to start',
    'conversation.requesting_permission': 'Requesting microphone permission...',
    'conversation.connected': 'Connected',
    'conversation.reconnecting': 'Reconnecting...',
    'conversation.listening': 'Listening...',
    'conversation.processing': 'Processing...',
    'conversation.speaking': 'Speaking...',
    'conversation.interrupted': 'Interrupted',
    'conversation.connecting': 'Connecting...',
    'conversation.error': 'Connection error',
    'conversation.disconnected': 'Disconnected',
    'conversation.stopSpeaking': 'Stop Speaking',
    'conversation.repeat': 'Repeat Answer',
    'conversation.end': 'End Conversation',
    'conversation.microphone': 'Microphone',
    'conversation.noSpeech': 'No speech detected. Please try again.',
    'conversation.unclear': 'Could not understand. Please speak again.',
    'conversation.startHint': 'Press the microphone button to start a conversation',
    'settings.language': 'Language',
    'settings.accessibility': 'Accessibility',
    'settings.largeText': 'Large Text',
    'settings.highContrast': 'High Contrast',
    'settings.reducedMotion': 'Reduced Motion',
    'settings.volume': 'Volume',
    'settings.help': 'Help & Feedback',
    'settings.about': 'About',
    'error.micPermission': 'Microphone permission denied. Please enable in browser settings.',
    'error.network': 'Network error. Please check your connection.',
    'error.api': 'AI service unavailable. Please try again later.',
    'error.session': 'Session error. Please restart conversation.',
    'accessibility.screenReader': 'Screen reader optimized',
    'accessibility.keyboardNav': 'Keyboard navigation enabled',
    'accessibility.focusVisible': 'Focus indicators visible',
  },
  'hi-IN': {
    'app.name': 'सहायक AI',
    'app.tagline': 'आपका बहुभाषी वॉयस असिस्टेंट',
    'nav.home': 'होम',
    'nav.conversation': 'बातचीत',
    'home.welcome': 'सहायक AI में आपका स्वागत है',
    'home.subtitle': 'माइक्रोफोन दबाएं और स्वाभाविक रूप से बोलें। मैं आपकी भाषा में जवाब दूंगा।',
    'home.selectLanguage': 'अपनी भाषा चुनें',
    'home.startConversation': 'बातचीत शुरू करें',
    'home.categories.title': 'मैं आपकी कैसे मदद कर सकता हूँ?',
    'home.categories.agriculture': 'कृषि सहायता',
    'home.categories.agriculture.desc': 'फसल सलाह, मौसम, बाजार भाव',
    'home.categories.government': 'सरकारी योजनाएं',
    'home.categories.government.desc': 'लाभ, आवेदन, पात्रता',
    'home.categories.transport': 'परिवहन जानकारी',
    'home.categories.transport.desc': 'रास्ते, समय सारणी, किराया',
    'home.categories.hospital': 'अस्पताल सहायता',
    'home.categories.hospital.desc': 'अस्पताल खोजें, अपॉइंटमेंट बुक करें',
    'home.accessibility': 'सुगम्यता',
    'home.settings': 'सेटिंग्स',
    'conversation.idle': 'शुरू करने के लिए तैयार',
    'conversation.requesting_permission': 'माइक्रोफ़ोन की अनुमति मांगी जा रही है...',
    'conversation.connected': 'कनेक्ट हो गया',
    'conversation.reconnecting': 'पुनः कनेक्ट हो रहा है...',
    'conversation.listening': 'सुन रहा हूँ...',
    'conversation.processing': 'प्रोसेसिंग...',
    'conversation.speaking': 'बोल रहा हूँ...',
    'conversation.interrupted': 'बाधित',
    'conversation.connecting': 'कनेक्ट हो रहा है...',
    'conversation.error': 'कनेक्शन त्रुटि',
    'conversation.disconnected': 'डिस्कनेक्टेड',
    'conversation.stopSpeaking': 'बोलना बंद करें',
    'conversation.repeat': 'जवाब दोहराएं',
    'conversation.end': 'बातचीत समाप्त करें',
    'conversation.microphone': 'माइक्रोफोन',
    'conversation.noSpeech': 'कोई आवाज़ नहीं मिली। कृपया फिर से कोशिश करें।',
    'conversation.unclear': 'समझ नहीं आया। कृपया फिर से बोलें।',
    'conversation.startHint': 'बातचीत शुरू करने के लिए माइक्रोफोन बटन दबाएं',
    'settings.language': 'भाषा',
    'settings.accessibility': 'सुगम्यता',
    'settings.largeText': 'बड़ा टेक्स्ट',
    'settings.highContrast': 'हाई कंट्रास्ट',
    'settings.reducedMotion': 'कम मोशन',
    'settings.volume': 'आवाज़',
    'settings.help': 'मदद और प्रतिक्रिया',
    'settings.about': 'जानकारी',
    'error.micPermission': 'माइक्रोफोन की अनुमति नहीं दी गई। ब्राउज़र सेटिंग्स में सक्षम करें।',
    'error.network': 'नेटवर्क त्रुटि। कृपया कनेक्शन जांचें।',
    'error.api': 'AI सेवा उपलब्ध नहीं। बाद में कोशिश करें।',
    'error.session': 'सत्र त्रुटि। कृपया बातचीत पुनः आरंभ करें।',
    'accessibility.screenReader': 'स्क्रीन रीडर के लिए अनुकूलित',
    'accessibility.keyboardNav': 'कीबोर्ड नेविगेशन सक्षम',
    'accessibility.focusVisible': 'फोकस संकेतक दृश्यमान',
  },
};

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [languageCode, setLanguageCode] = useState<LanguageCode>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('sahayak-language') as LanguageCode | null;
      if (stored && SUPPORTED_LANGUAGES.some(l => l.code === stored)) {
        return stored;
      }
      const browserLang = navigator.language;
      if (browserLang.startsWith('hi')) return 'hi-IN';
    }
    return DEFAULT_LANGUAGE;
  });

  const currentLanguage = getLanguage(languageCode);

  useEffect(() => {
    localStorage.setItem('sahayak-language', languageCode);
    document.documentElement.lang = languageCode;
    document.documentElement.className = document.documentElement.className
      .replace(/lang-\w+/g, '')
      .trim() + ` lang-${languageCode.split('-')[0]}`;
  }, [languageCode]);

  const setLanguage = useCallback((code: LanguageCode) => {
    setLanguageCode(code);
  }, []);

  const t = useCallback((key: string, params?: Record<string, string | number>) => {
    let translation = translations[languageCode][key] || translations[DEFAULT_LANGUAGE][key] || key;
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        translation = translation.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
      });
    }
    return translation;
  }, [languageCode]);

  return (
    <LanguageContext.Provider value={{ currentLanguage, languageCode, setLanguage, supportedLanguages: SUPPORTED_LANGUAGES, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}