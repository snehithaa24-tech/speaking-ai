



























import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Settings, LogOut, User } from 'lucide-react';
import { cn } from '@utils/cn';
import { useLanguage } from '@contexts/LanguageContext';
import { useAuth } from '@contexts/AuthContext';
import { Button } from '@components/shared/Button';
import { LanguageSelector } from '@components/accessibility/LanguageSelector';
import { AccessibilitySettings } from '@components/accessibility/AccessibilitySettings';
import { Loader2 } from 'lucide-react';

export function Header() {
  const { t } = useLanguage();
  const { user, isAuthenticated, logout, login } = useAuth();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showAccessibility, setShowAccessibility] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const navigation = [
    { path: '/', label: t('nav.home') || 'Home' },
    { path: '/conversation', label: t('nav.conversation') || 'Conversation' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="sticky top-0 z-50 bg-background-primary/95 backdrop-blur-md border-b border-border-primary">
      <div className="container-app">
        <div className="flex h-16 items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2" aria-label="SAHAYAK AI Home">
            <svg className="h-8 w-8 text-brand-primary" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <rect width="32" height="32" rx="8" fill="currentColor" />
              <path d="M16 8C12.6863 8 10 10.6863 10 14C10 15.2867 10.4029 16.4885 11.134 17.4671L10.3629 20.2009C10.1958 20.6153 10.5679 21.0625 11.023 20.988L13.359 20.3253C14.2072 21.0021 15.2963 21.45 16.4536 21.625C18.0028 21.7787 19.45 21.45 20.5 20.625C21.2707 20.0293 21.625 18.85 21.45 17.375C21.293 15.9912 20.6945 14.75 19.75 13.875C19.0193 13.1786 18.0265 12.7169 17.021 12.666C16.5193 12.6477 16.0385 12.8378 15.7037 13.1726L14.9445 10.3529C14.8555 9.98212 14.4877 9.6672 14.0733 9.59271C13.6589 9.51822 13.2403 9.68643 12.9714 10.0083L11.95 11.75C11.2689 10.8436 10.2857 10.25 9.125 10.0313C7.5803 9.75 6.17383 10.2031 5.21875 11.3125C4.26367 12.4219 3.875 13.8906 4.09375 15.3125C4.41562 17.4375 5.72656 19.3125 7.78125 20.5C9.83594 21.6875 12.3438 22.125 14.9375 21.75C16.3458 21.5391 17.65 20.9318 18.5938 20.0313C19.5375 19.1307 20.125 18.0078 20.2813 16.7813C20.4375 15.5547 20.0938 14.25 19.3125 13.2188C18.6094 12.2852 17.6211 11.5577 16.5156 11.3281C15.6641 11.1445 14.7617 11.4688 14.1406 12.125C13.5195 12.7813 13.1875 13.6328 13.1563 14.5625C13.125 15.6563 13.5391 16.6563 14.2813 17.3125C15.0234 17.9688 16.0078 18.25 17 18.0938C17.8359 17.9609 18.4844 17.5391 18.8125 16.9375C19.1406 16.3359 19.1094 15.5859 18.75 14.9375C18.3906 14.2891 17.7734 13.75 17.0313 13.4688C16.2891 13.1875 15.4766 13.2188 14.8281 13.5938C14.1797 13.9688 13.75 14.625 13.6563 15.4375C13.5625 16.25 13.8047 17.0781 14.375 17.6563C14.9453 18.2344 15.7578 18.4375 16.5 18.2813C17.3438 18.125 18.0313 17.6563 18.4063 17.0313C19.5375 19.1307 20.125 18.0078 20.2813 16.7813C20.4375 15.5547 20.0938 14.25 19.3125 13.2188C18.6094 12.2852 17.6211 11.5577 16.5156 11.3281C15.6641 11.1445 14.7617 11.4688 14.1406 12.125C13.5195 12.7813 13.1875 13.6328 13.1563 14.5625C13.125 15.6563 13.5391 16.6563 14.2813 17.3125C15.0234 17.9688 16.0078 18.25 17 18.0938C17.8359 17.9609 18.4844 17.5391 18.8125 16.9375C19.1406 16.3359 19.1094 15.5859 18.75 14.9375C18.3906 14.2891 17.7734 13.75 17.0313 13.4688C16.2891 13.1875 15.4766 13.2188 14.8281 13.5938C14.1797 13.9688 13.75 14.625 13.6563 15.4375C13.5625 16.25 13.8047 17.0781 14.375 17.6563C14.9453 18.2344 15.7578 18.4375 16.5 18.2813C17.3438 18.125 18.0313 17.6563 18.4063 17.0313" fill="white" />
            </svg>
            <span className="text-h4 font-semibold text-foreground-primary hidden sm:block">SAHAYAK AI</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
            {navigation.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  'px-3 py-2 rounded-lg text-body-sm font-medium transition-colors',
                  isActive(item.path)
                    ? 'bg-brand-muted text-brand-primary'
                    : 'text-foreground-secondary hover:text-foreground-primary hover:bg-background-tertiary'
                )}
                aria-current={isActive(item.path) ? 'page' : undefined}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <LanguageSelector variant="pills" onChange={() => setShowSettings(false)} />

            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowAccessibility(true)}
              aria-label={t('home.accessibility')}
              aria-expanded={showAccessibility}
            >
              <Settings className="h-5 w-5" aria-hidden="true" />
            </Button>

            {isAuthenticated ? (
              <div className="relative">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowSettings(!showSettings)}
                  aria-label="User menu"
                  aria-expanded={showSettings}
                >
                  <User className="h-5 w-5" aria-hidden="true" />
                </Button>
                {showSettings && (
                  <div className="absolute right-0 mt-2 w-48 bg-background-primary border border-border-primary rounded-xl shadow-strong py-2">
                    <div className="px-4 py-2 border-b border-border-primary">
                      <p className="font-medium text-body-sm text-foreground-primary">{user?.name || 'User'}</p>
                      <p className="text-caption text-foreground-muted">{user?.email}</p>
                    </div>
                    <button
                      onClick={logout}
                      className="w-full px-4 py-2 text-left text-body-sm text-foreground-secondary hover:text-foreground-primary hover:bg-background-tertiary"
                    >
                      <LogOut className="h-4 w-4 mr-2 inline" aria-hidden="true" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Button
                variant="primary"
                size="sm"
                className="hidden sm:inline-flex"
                onClick={() => {
                  setIsLoggingIn(true);
                  login();
                  // Reset loading state after a delay since login redirects
                  setTimeout(() => setIsLoggingIn(false), 5000);
                }}
                disabled={isLoggingIn}
              >
                {isLoggingIn ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Sign In
              </Button>
            )}

            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              aria-label="Menu"
              aria-expanded={isMenuOpen}
            >
              {isMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>

        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-border-primary animate-slide-down">
            <nav className="flex flex-col gap-2">
              {navigation.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsMenuOpen(false)}
                  className={cn(
                    'px-3 py-2 rounded-lg text-body font-medium',
                    isActive(item.path)
                      ? 'bg-brand-muted text-brand-primary'
                      : 'text-foreground-secondary hover:bg-background-tertiary'
                  )}
                >
                  {item.label}
                </Link>
              ))}
              {!isAuthenticated && (
                <Button
                  variant="primary"
                  size="sm"
                  fullWidth
                  onClick={() => {
                    setIsMenuOpen(false);
                    setIsLoggingIn(true);
                    login();
                    setTimeout(() => setIsLoggingIn(false), 5000);
                  }}
                  disabled={isLoggingIn}
                  className="mt-2 sm:hidden"
                >
                  {isLoggingIn ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Sign In with Google
                </Button>
              )}
            </nav>
          </div>
        )}
      </div>

      {showAccessibility && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/50 animate-fade-in">
          <div className="w-full max-w-md max-h-[90vh] overflow-y-auto bg-background-primary rounded-t-2xl sm:rounded-xl shadow-strong animate-slide-up">
            <div className="sticky top-0 bg-background-primary border-b border-border-primary p-4 flex items-center justify-between">
              <h2 className="text-h4 font-semibold text-foreground-primary">{t('settings.accessibility')}</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowAccessibility(false)} aria-label="Close">
                <X className="h-5 w-5" />
              </Button>
            </div>
            <div className="p-4">
              <AccessibilitySettings />
            </div>
          </div>
        </div>
      )}

      {showSettings && !isAuthenticated && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 animate-fade-in">
          <div className="w-full max-w-md bg-background-primary rounded-xl shadow-strong p-6 animate-scale-in">
            <h2 className="text-h4 font-semibold text-foreground-primary mb-4">Sign In</h2>
            <p className="text-body text-foreground-secondary mb-6">Sign in with Google to sync your preferences across devices.</p>
            <Button
              variant="primary"
              fullWidth
              onClick={() => {
                setShowSettings(false);
                setIsLoggingIn(true);
                login();
                setTimeout(() => setIsLoggingIn(false), 5000);
              }}
              disabled={isLoggingIn}
              className="mb-3"
            >
              <svg className="h-5 w-5 mr-2" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              {isLoggingIn ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Redirecting...
                </>
              ) : (
                'Continue with Google'
              )}
            </Button>
            <Button variant="secondary" fullWidth onClick={() => setShowSettings(false)}>
              Continue without account
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}