import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import type { Language } from '../types';
import LoginBrandPanel from './login/LoginBrandPanel';
import PasswordField from './login/PasswordField';
import { LOGIN_TEXT } from './login/loginText';
import { useBackendStatus, type BackendStatus } from './login/useBackendStatus';
import './login/LoginPage.css';

// Public demo account; the button is hidden when these are not set at build time.
const DEMO_EMAIL: string | undefined = import.meta.env.VITE_DEMO_EMAIL;
const DEMO_PASSWORD: string | undefined = import.meta.env.VITE_DEMO_PASSWORD;

interface LoginPageProps {
  language: Language;
  onToggleLanguage: () => void;
}

export default function LoginPage({ language, onToggleLanguage }: LoginPageProps) {
  const { login, sessionExpired } = useAuth();
  const text = LOGIN_TEXT[language];
  const status = useBackendStatus();
  const [error, setError] = useState<keyof typeof text | null>(null);
  const [loading, setLoading] = useState(false);
  // Uncontrolled: Chrome autofill values are only readable from the DOM after a user action.
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const signIn = async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      if (passwordRef.current) passwordRef.current.value = '';
      // Generic messages: never reveal which field was wrong or echo backend detail.
      setError(err instanceof ApiError && err.status === 401 ? 'failed' : 'unavailable');
      passwordRef.current?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (loading) return;
    const email = emailRef.current?.value.trim() ?? '';
    const password = passwordRef.current?.value ?? '';
    if (!email || !password) {
      setError('required');
      (email ? passwordRef : emailRef).current?.focus();
      return;
    }
    void signIn(email, password);
  };

  return (
    <div className="login-root">
      <LoginBrandPanel text={text} />

      <main className="login-main">
        <div className="login-form-col">
          {sessionExpired && (
            <p className="login-banner login-banner--info" role="status">{text.sessionExpired}</p>
          )}

          <h1 className="login-title">{text.title}</h1>
          <p className="login-subtitle">{text.subtitle}</p>

          <form
            className="login-form"
            onSubmit={handleSubmit}
            onInput={() => setError(prev => (prev === 'required' ? null : prev))}
            noValidate
            aria-busy={loading}
          >
            <div>
              <label className="login-label" htmlFor="login-email">{text.email}</label>
              <input
                id="login-email"
                ref={emailRef}
                name="email"
                type="email"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                placeholder="you@example.com"
                className="login-input"
                aria-required="true"
              />
            </div>

            <PasswordField id="login-password" inputRef={passwordRef} text={text} />

            {error && (
              <p className="login-banner login-banner--error" role="alert" data-testid="login-error">
                {text[error]}
              </p>
            )}

            {/* Disabled via colors, not opacity, so the label does not render as a lighter box. */}
            <button type="submit" className="login-submit" disabled={loading}>
              {loading && <span className="login-spinner" aria-hidden="true" />}
              {text.submit}
              {!loading && <ArrowIcon />}
            </button>
          </form>

          {DEMO_EMAIL && DEMO_PASSWORD && (
            <div className="login-demo">
              <div>
                <p className="login-demo__title">{text.demoTitle}</p>
                <p className="login-demo__text">{text.demoText}</p>
              </div>
              <button
                type="button"
                className="login-demo__button"
                disabled={loading}
                onClick={() => void signIn(DEMO_EMAIL, DEMO_PASSWORD)}
              >
                {text.demoButton}
              </button>
            </div>
          )}

          <p className="login-notice">
            <ShieldIcon />
            {text.notice}
          </p>

          <div className="login-status-row">
            <StatusLine status={status} text={text} />
            <button type="button" className="login-lang" onClick={onToggleLanguage} lang={language === 'en' ? 'el' : 'en'}>
              {text.languageToggle}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

const STATUS_LABEL: Record<BackendStatus, keyof typeof LOGIN_TEXT['en']> = {
  checking: 'statusChecking',
  waking: 'statusWaking',
  ready: 'statusReady',
  degraded: 'statusDegraded',
  offline: 'statusOffline',
};

function StatusLine({ status, text }: { status: BackendStatus; text: typeof LOGIN_TEXT['en'] }) {
  return (
    <span className="login-status" data-status={status} data-testid="backend-status" role="status">
      <span className="login-status__dot" aria-hidden="true" />
      {text[STATUS_LABEL[status]]}
    </span>
  );
}

const ArrowIcon = () => (
  <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
  </svg>
);

const ShieldIcon = () => (
  <svg className="login-notice__icon" width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z" /><polyline points="9 12 11 14 15 10" />
  </svg>
);
