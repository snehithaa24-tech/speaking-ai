import { Link } from 'react-router-dom';
import { Github, Twitter, Mail, Heart } from 'lucide-react';

export function Footer() {

  const footerLinks = {
    product: [
      { label: 'Features', href: '/conversation' },
      { label: 'Documentation', href: 'http://localhost:8000/docs' },
      { label: 'Settings', href: '/settings' },
    ],
    company: [
      { label: 'About', href: '/settings' },
      { label: 'Contact', href: '/settings' },
    ],
    legal: [
      { label: 'Privacy', href: '/settings' },
      { label: 'Terms', href: '/settings' },
    ],
    resources: [
      { label: 'Help Center', href: '/settings' },
      { label: 'API Docs', href: 'http://localhost:8000/docs' },
    ],
  };

  const socialLinks = [
    { icon: Github, href: 'https://github.com', label: 'GitHub' },
    { icon: Twitter, href: 'https://twitter.com', label: 'Twitter' },
    { icon: Mail, href: 'mailto:support@sahayak.ai', label: 'Email' },
  ];

  return (
    <footer className="bg-background-secondary border-t border-border-primary" role="contentinfo">
      <div className="container-app py-12 lg:py-16">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 lg:gap-12">
          <div className="col-span-2 md:col-span-1">
            <Link to="/" className="flex items-center gap-2 mb-4" aria-label="SAHAYAK AI Home">
              <svg className="h-8 w-8 text-brand-primary" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                <rect width="32" height="32" rx="8" fill="currentColor" />
                <path d="M16 8C12.6863 8 10 10.6863 10 14C10 15.2867 10.4029 16.4885 11.134 17.4671L10.3629 20.2009C10.1958 20.6153 10.5679 21.0625 11.023 20.988L13.359 20.3253C14.2072 21.0021 15.2963 21.45 16.4536 21.625C18.0028 21.7787 19.45 21.45 20.5 20.625C21.2707 20.0293 21.625 18.85 21.45 17.375C21.293 15.9912 20.6945 14.75 19.75 13.875C19.0193 13.1786 18.0265 12.7169 17.021 12.666C16.5193 12.6477 16.0385 12.8378 15.7037 13.1726L14.9445 10.3529C14.8555 9.98212 14.4877 9.6672 14.0733 9.59271C13.6589 9.51822 13.2403 9.68643 12.9714 10.0083L11.95 11.75C11.2689 10.8436 10.2857 10.25 9.125 10.0313C7.5803 9.75 6.17383 10.2031 5.21875 11.3125C4.26367 12.4219 3.875 13.8906 4.09375 15.3125C4.41562 17.4375 5.72656 19.3125 7.78125 20.5C9.83594 21.6875 12.3438 22.125 14.9375 21.75C16.3458 21.5391 17.65 20.9318 18.5938 20.0313C19.5375 19.1307 20.125 18.0078 20.2813 16.7813C20.4375 15.5547 20.0938 14.25 19.3125 13.2188C18.6094 12.2852 17.6211 11.5577 16.5156 11.3281C15.6641 11.1445 14.7617 11.4688 14.1406 12.125C13.5195 12.7813 13.1875 13.6328 13.1563 14.5625C13.125 15.6563 13.5391 16.6563 14.2813 17.3125C15.0234 17.9688 16.0078 18.25 17 18.0938C17.8359 17.9609 18.4844 17.5391 18.8125 16.9375C19.1406 16.3359 19.1094 15.5859 18.75 14.9375C18.3906 14.2891 17.7734 13.75 17.0313 13.4688C16.2891 13.1875 15.4766 13.2188 14.8281 13.5938C14.1797 13.9688 13.75 14.625 13.6563 15.4375C13.5625 16.25 13.8047 17.0781 14.375 17.6563C14.9453 18.2344 15.7578 18.4375 16.5 18.2813C17.3438 18.125 18.0313 17.6563 18.4063 17.0313" fill="white"/>
              </svg>
              <span className="text-h4 font-semibold text-foreground-primary">SAHAYAK AI</span>
            </Link>
            <p className="text-body text-foreground-secondary mb-6 max-w-xs">
              Multilingual voice assistant for accessibility. Built with care for everyone.
            </p>
            <div className="flex items-center gap-4">
              {socialLinks.map(({ icon: Icon, href, label }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-foreground-muted hover:text-brand-primary transition-colors"
                  aria-label={label}
                >
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </a>
              ))}
            </div>
          </div>

          {[
            { title: 'Product', links: footerLinks.product, label: 'Product links' },
            { title: 'Company', links: footerLinks.company, label: 'Company links' },
            { title: 'Legal', links: footerLinks.legal, label: 'Legal links' },
            { title: 'Resources', links: footerLinks.resources, label: 'Resource links' },
          ].map(({ title, links, label }) => (
            <nav key={title} aria-label={label}>
              <h3 className="font-semibold text-foreground-primary mb-4">{title}</h3>
              <ul className="space-y-3" role="list">
                {links.map(({ label: linkLabel, href }) => (
                  <li key={linkLabel}>
                    {href.startsWith('http') ? (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-body-sm text-foreground-secondary hover:text-brand-primary transition-colors inline-flex items-center gap-1"
                      >
                        {linkLabel}
                        <span className="sr-only">(opens in new window)</span>
                      </a>
                    ) : (
                      <Link
                        to={href}
                        className="text-body-sm text-foreground-secondary hover:text-brand-primary transition-colors"
                      >
                        {linkLabel}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-12 pt-8 border-t border-border-primary">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-body-sm text-foreground-muted">
              © {new Date().getFullYear()} SAHAYAK AI. All rights reserved.
            </p>
            <p className="flex items-center gap-2 text-body-sm text-foreground-muted">
              Made with <Heart className="h-4 w-4 text-error-secondary" aria-hidden="true" /> for accessibility
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}