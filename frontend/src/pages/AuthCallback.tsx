import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '@contexts/AuthContext';
import { apiService } from '@services/api';
import { Button } from '@components/shared/Button';

export function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    let isMounted = true;

    async function handleCallback() {
      const error = searchParams.get('error');
      const code = searchParams.get('code');

      if (error) {
        if (!isMounted) return;
        setStatus('error');
        setErrorMessage(`Google authentication error: ${error}`);
        return;
      }

      if (!code) {
        if (!isMounted) return;
        setStatus('error');
        setErrorMessage('No authorization code was provided by Google.');
        return;
      }

      try {
        const redirectUri = `${window.location.origin}/auth/callback`;
        const res = await apiService.googleAuth(code, redirectUri);

        if (!isMounted) return;

        if (res.success && res.data?.accessToken) {
          localStorage.setItem('sahayak-token', res.data.accessToken);

          // Fetch current user details
          const userRes = await apiService.getCurrentUser(res.data.accessToken);
          if (userRes.success && userRes.data) {
            updateUser(userRes.data);
          }

          setStatus('success');
          setTimeout(() => {
            navigate('/conversation', { replace: true });
          }, 1000);
        } else {
          setStatus('error');
          setErrorMessage(res.error || 'Authentication token exchange failed.');
        }
      } catch (err) {
        if (!isMounted) return;
        setStatus('error');
        setErrorMessage(err instanceof Error ? err.message : 'Unexpected authentication error');
      }
    }

    handleCallback();

    return () => {
      isMounted = false;
    };
  }, [searchParams, navigate, updateUser]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-background-secondary border border-border-primary rounded-2xl p-8 shadow-card text-center space-y-4">
        {status === 'loading' && (
          <div className="space-y-4">
            <Loader2 className="w-10 h-10 text-brand-primary animate-spin mx-auto" aria-hidden="true" />
            <h1 className="text-h3 font-semibold text-foreground-primary">Authenticating...</h1>
            <p className="text-body-sm text-foreground-secondary">
              Verifying your Google credentials with SAHAYAK AI.
            </p>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4">
            <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto" aria-hidden="true" />
            <h1 className="text-h3 font-semibold text-foreground-primary">Login Successful!</h1>
            <p className="text-body-sm text-foreground-secondary">
              Redirecting you to your voice assistant...
            </p>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4">
            <AlertCircle className="w-10 h-10 text-error-secondary mx-auto" aria-hidden="true" />
            <h1 className="text-h3 font-semibold text-foreground-primary">Sign In Failed</h1>
            <p className="text-body-sm text-error-primary bg-error-secondary/10 p-3 rounded-lg border border-error-secondary/20">
              {errorMessage}
            </p>
            <div className="pt-2 flex flex-col sm:flex-row gap-2 justify-center">
              <Button variant="primary" onClick={() => navigate('/conversation')}>
                Continue to App
              </Button>
              <Button variant="ghost" onClick={() => navigate('/')}>
                Return Home
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

