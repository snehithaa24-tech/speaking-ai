import { Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { Footer } from './Footer';
import { cn } from '@utils/cn';
import { useLanguage } from '@contexts/LanguageContext';
import { getLanguage } from '@/types';

interface LayoutProps {
  className?: string;
}

export function Layout({ className }: LayoutProps) {
  const { languageCode } = useLanguage();
  const language = getLanguage(languageCode);
  const location = useLocation();
  const isConversation = location.pathname === '/conversation';

  return (
    <div
      className={cn('min-h-screen flex flex-col', className)}
      dir={language.direction}
    >
      <Header />
      <main
        className={cn('flex-1', isConversation && 'flex flex-col min-h-0 overflow-hidden')}
        id="main-content"
        role="main"
      >
        <Outlet />
      </main>
      {!isConversation && <Footer />}
    </div>
  );
}

export function AuthLayout({ className }: LayoutProps) {
  return (
    <div className={cn('min-h-screen flex flex-col', className)}>
      <Header />
      <main className="flex-1 flex items-center justify-center p-4" id="main-content" role="main">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}