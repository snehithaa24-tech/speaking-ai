import { useLanguage } from '@contexts/LanguageContext';
import { useAuth } from '@contexts/AuthContext';
import { LanguageSelector } from '@components/accessibility/LanguageSelector';
import { AccessibilitySettings } from '@components/accessibility/AccessibilitySettings';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@components/shared/Card';
import { Button } from '@components/shared/Button';
import { User, LogOut, Shield, Info, ExternalLink } from 'lucide-react';

export function Settings() {
  const { t, setLanguage } = useLanguage();
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <div className="min-h-screen py-12">
      <div className="container-app max-w-3xl">
        <div className="mb-8">
          <h1 className="text-h1 font-bold text-foreground-primary mb-2">{t('home.settings')}</h1>
          <p className="text-body-lg text-foreground-secondary">Manage your preferences and account settings</p>
        </div>

        <Card variant="hover">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-brand-muted text-brand-primary rounded-lg">
                <Shield className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <CardTitle>{t('settings.language')}</CardTitle>
                <CardDescription>Choose your preferred language for conversations</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <LanguageSelector variant="grid" onChange={setLanguage} />
          </CardContent>
        </Card>

        <Card variant="hover" className="mt-6">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-success-muted text-success-primary rounded-lg">
                <User className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <CardTitle>Accessibility</CardTitle>
                <CardDescription>Customize the experience for your needs</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <AccessibilitySettings />
          </CardContent>
        </Card>

        <Card variant="hover" className="mt-6">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                <Info className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <CardTitle>About</CardTitle>
                <CardDescription>Version and legal information</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <dl className="space-y-3 text-body-sm">
              <div className="flex justify-between">
                <dt className="text-foreground-secondary">Version</dt>
                <dd className="text-foreground-primary font-medium">1.0.0</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-foreground-secondary">Environment</dt>
                <dd className="text-foreground-primary font-medium">Development</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-foreground-secondary">AI Model</dt>
                <dd className="text-foreground-primary font-medium">Gemini Live</dd>
              </div>
            </dl>
            <div className="pt-4 border-t border-border-primary space-y-2">
              <a href="/docs/architecture.md" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-body-sm text-brand-primary hover:underline">
                Architecture Documentation
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
              <a href="/docs/api.md" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-body-sm text-brand-primary hover:underline">
                API Documentation
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
              <a href="/docs/testing.md" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-body-sm text-brand-primary hover:underline">
                Testing Guide
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
              <a href="/docs/deployment.md" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-body-sm text-brand-primary hover:underline">
                Deployment Guide
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            </div>
          </CardContent>
        </Card>

        {isAuthenticated && (
          <Card variant="hover" className="mt-6 border-error-muted">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-error-muted text-error-primary rounded-lg">
                  <LogOut className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <CardTitle>Account</CardTitle>
                  <CardDescription>Manage your account and sign out</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4 p-4 bg-background-secondary rounded-lg mb-4">
                <div className="w-10 h-10 rounded-full bg-brand-muted text-brand-primary flex items-center justify-center font-medium">
                  {user?.name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div>
                  <p className="font-medium text-body text-foreground-primary">{user?.name || 'User'}</p>
                  <p className="text-body-sm text-foreground-muted">{user?.email}</p>
                </div>
              </div>
              <Button variant="danger" onClick={logout} fullWidth>
                <LogOut className="h-4 w-4 mr-2" aria-hidden="true" />
                Sign Out
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

