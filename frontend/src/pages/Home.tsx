import { Link } from 'react-router-dom';
import { Mic, Wheat, Building, Bus, Hospital, ArrowRight, Shield, Languages, Volume2 } from 'lucide-react';
import { cn } from '@utils/cn';
import { useLanguage } from '@contexts/LanguageContext';
import { Button } from '@components/shared/Button';
import { Card, CardContent, CardTitle, CardDescription } from '@components/shared/Card';
import { LanguageSelector } from '@components/accessibility/LanguageSelector';
import { ConnectionStatus } from '@components/voice/ConnectionStatus';

const categories = [
  {
    id: 'agriculture',
    icon: Wheat,
    title: 'home.categories.agriculture',
    description: 'home.categories.agriculture.desc',
    href: '/conversation?category=agriculture',
    color: 'text-amber-600 bg-amber-50',
  },
  {
    id: 'government',
    icon: Building,
    title: 'home.categories.government',
    description: 'home.categories.government.desc',
    href: '/conversation?category=government',
    color: 'text-blue-600 bg-blue-50',
  },
  {
    id: 'transport',
    icon: Bus,
    title: 'home.categories.transport',
    description: 'home.categories.transport.desc',
    href: '/conversation?category=transport',
    color: 'text-green-600 bg-green-50',
  },
  {
    id: 'hospital',
    icon: Hospital,
    title: 'home.categories.hospital',
    description: 'home.categories.hospital.desc',
    href: '/conversation?category=hospital',
    color: 'text-red-600 bg-red-50',
  },
];

const features = [
  {
    icon: Mic,
    title: 'home.features.voice.title',
    description: 'home.features.voice.desc',
  },
  {
    icon: Languages,
    title: 'home.features.multilingual.title',
    description: 'home.features.multilingual.desc',
  },
  {
    icon: Shield,
    title: 'home.features.privacy.title',
    description: 'home.features.privacy.desc',
  },
  {
    icon: Volume2,
    title: 'home.features.accessibility.title',
    description: 'home.features.accessibility.desc',
  },
];

export function Home() {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen">
      <section className="relative overflow-hidden py-16 lg:py-24" aria-labelledby="hero-heading">
        <div className="container-app">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-muted text-brand-primary text-body-sm font-medium mb-6 animate-fade-in">
              <Languages className="h-4 w-4" aria-hidden="true" />
              <span>{t('app.tagline')}</span>
            </div>

            <h1 id="hero-heading" className="text-display font-bold text-foreground-primary mb-6 animate-slide-up">
              {t('app.name')}
            </h1>

            <p className="text-body-lg text-foreground-secondary mb-10 max-w-2xl mx-auto animate-slide-up" style={{ animationDelay: '100ms' }}>
              {t('home.subtitle')}
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up" style={{ animationDelay: '200ms' }}>
              <Link to="/conversation">
                <Button variant="primary" size="lg" rightIcon={<ArrowRight className="h-5 w-5" />}>
                  {t('home.startConversation')}
                </Button>
              </Link>
              <Button variant="secondary" size="lg" onClick={() => document.getElementById('categories')?.scrollIntoView({ behavior: 'smooth' })}>
                Explore Categories
              </Button>
            </div>

            <div className="mt-10 flex items-center justify-center gap-8 text-body-sm text-foreground-muted animate-fade-in" style={{ animationDelay: '300ms' }} role="status" aria-live="polite">
              <ConnectionStatus status="disconnected" compact showLabel={false} />
              <span>Select a language and start talking</span>
              <LanguageSelector variant="pills" />
            </div>
          </div>
        </div>
      </section>

      <section id="categories" className="py-16 lg:py-24 bg-background-secondary" aria-labelledby="categories-heading">
        <div className="container-app">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 id="categories-heading" className="text-h2 font-bold text-foreground-primary mb-4">
              {t('home.categories.title')}
            </h2>
            <p className="text-body-lg text-foreground-secondary">
              Tap a category to start a conversation about that topic
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6" role="list">
            {categories.map((category) => (
              <article key={category.id} className="group" role="listitem">
                <Link to={category.href} className="block">
                  <Card variant="hover" className="h-full">
                    <CardContent className="p-6 flex flex-col h-full">
                      <div className={cn('p-3 rounded-xl', category.color, 'mb-4 group-hover:scale-110 transition-transform')}>
                        <category.icon className="h-7 w-7" aria-hidden="true" />
                      </div>
                      <CardTitle className="text-h4">{t(category.title)}</CardTitle>
                      <CardDescription className="flex-1">{t(category.description)}</CardDescription>
                      <div className="flex items-center gap-2 mt-4 text-body-sm text-foreground-muted group-hover:text-brand-primary transition-colors">
                        <span>Start conversation</span>
                        <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 lg:py-24" aria-labelledby="features-heading">
        <div className="container-app">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 id="features-heading" className="text-h2 font-bold text-foreground-primary mb-4">
              Why SAHAYAK AI?
            </h2>
            <p className="text-body-lg text-foreground-secondary">
              Designed for natural, accessible voice interactions
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature) => (
              <Card key={feature.title} variant="hover" className="text-center">
                <CardContent className="p-6">
                  <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-brand-muted text-brand-primary mb-4">
                    <feature.icon className="h-7 w-7" aria-hidden="true" />
                  </div>
                  <CardTitle className="text-h4">{t(feature.title)}</CardTitle>
                  <CardDescription>{t(feature.description)}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 lg:py-24 bg-background-secondary" aria-labelledby="accessibility-heading">
        <div className="container-app">
          <div className="max-w-3xl mx-auto text-center">
            <h2 id="accessibility-heading" className="text-h2 font-bold text-foreground-primary mb-4">
              {t('home.accessibility')}
            </h2>
            <p className="text-body-lg text-foreground-secondary mb-8">
              Built with accessibility as a priority, not an afterthought
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 text-left">
              {[
                { label: 'Large text mode', description: 'Scale UI text for better readability' },
                { label: 'High contrast', description: 'WCAG AA compliant color contrast' },
                { label: 'Reduced motion', description: 'Respects prefers-reduced-motion' },
                { label: 'Screen reader support', description: 'ARIA labels and live regions' },
                { label: 'Keyboard navigation', description: 'Full focus management' },
                { label: 'Audio replay', description: 'Repeat last response anytime' },
              ].map((item, index) => (
                <div key={index} className="flex items-start gap-3 p-4 bg-background-primary rounded-xl border border-border-primary">
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-brand-muted text-brand-primary flex items-center justify-center">
                    <Shield className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <p className="font-medium text-body text-foreground-primary">{item.label}</p>
                    <p className="text-body-sm text-foreground-secondary">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="py-16 lg:py-24" aria-labelledby="cta-heading">
        <div className="container-app">
          <div className="max-w-2xl mx-auto text-center">
            <h2 id="cta-heading" className="text-h2 font-bold text-foreground-primary mb-4">
              Ready to start?
            </h2>
            <p className="text-body-lg text-foreground-secondary mb-8">
              No account required. Just select your language and start talking.
            </p>
            <Link to="/conversation">
              <Button variant="primary" size="lg" rightIcon={<ArrowRight className="h-5 w-5" />}>
                {t('home.startConversation')}
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}