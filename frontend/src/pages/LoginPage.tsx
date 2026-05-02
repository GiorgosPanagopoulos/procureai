import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

const S = {
  root: {
    height: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--bg)',
    position: 'relative' as const,
    overflow: 'hidden',
  },
  ambient: {
    position: 'fixed' as const,
    inset: 0,
    pointerEvents: 'none' as const,
    background: `
      radial-gradient(ellipse 60% 40% at 20% 0%, rgba(59,123,255,0.07) 0%, transparent 70%),
      radial-gradient(ellipse 40% 30% at 80% 80%, rgba(34,211,238,0.04) 0%, transparent 70%)
    `,
  },
  card: {
    position: 'relative' as const,
    width: '100%',
    maxWidth: 400,
    background: 'rgba(14,18,32,0.75)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 20,
    padding: '36px 32px 32px',
    boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
    zIndex: 1,
  },
  logoRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    justifyContent: 'center',
    marginBottom: 8,
  },
  logoBox: {
    width: 32,
    height: 32,
    borderRadius: 9,
    background: 'linear-gradient(135deg, rgba(59,123,255,0.3), rgba(59,123,255,0.1))',
    border: '1px solid rgba(59,123,255,0.4)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoText: {
    fontFamily: 'var(--font-head)',
    fontWeight: 700,
    fontSize: 20,
    letterSpacing: '-0.02em',
    color: 'var(--text)',
  },
  subtitle: {
    textAlign: 'center' as const,
    fontSize: 13,
    color: 'var(--text2)',
    marginBottom: 28,
    lineHeight: 1.5,
  },
  tabs: {
    display: 'flex',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid var(--border)',
    borderRadius: 10,
    padding: 3,
    marginBottom: 24,
    gap: 3,
  },
  tabBtn: (active: boolean) => ({
    flex: 1,
    padding: '8px 0',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 13,
    fontFamily: 'var(--font-head)',
    fontWeight: 600,
    transition: 'all 0.15s',
    background: active ? 'var(--accent)' : 'transparent',
    color: active ? '#fff' : 'var(--text2)',
  }),
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 600,
    fontFamily: 'var(--font-head)',
    color: 'var(--text2)',
    marginBottom: 6,
    letterSpacing: '0.02em',
  },
  input: {
    width: '100%',
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid var(--border2)',
    borderRadius: 10,
    padding: '10px 14px',
    fontSize: 14,
    color: 'var(--text)',
    fontFamily: 'var(--font-body)',
    outline: 'none',
    marginBottom: 14,
    boxSizing: 'border-box' as const,
    transition: 'border-color 0.15s',
  },
  submit: {
    width: '100%',
    padding: '11px 0',
    background: 'var(--accent)',
    border: 'none',
    borderRadius: 10,
    color: '#fff',
    fontSize: 14,
    fontFamily: 'var(--font-head)',
    fontWeight: 700,
    cursor: 'pointer',
    marginTop: 4,
    transition: 'opacity 0.15s',
    letterSpacing: '0.01em',
  },
  error: {
    marginTop: 14,
    padding: '10px 14px',
    background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.25)',
    borderRadius: 8,
    fontSize: 13,
    color: '#f87171',
    lineHeight: 1.5,
  },
};

const LogoIcon = () => (
  <svg width={16} height={16} viewBox="0 0 24 24" fill="none">
    <rect x="3" y="3" width="8" height="8" rx="2" fill="#5e95ff" opacity=".9"/>
    <rect x="13" y="3" width="8" height="8" rx="2" fill="#5e95ff" opacity=".6"/>
    <rect x="3" y="13" width="8" height="8" rx="2" fill="#5e95ff" opacity=".6"/>
    <rect x="13" y="13" width="8" height="8" rx="2" fill="#5e95ff" opacity=".3"/>
  </svg>
);

export default function LoginPage() {
  const { login, register } = useAuth();
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      if (tab === 'login') {
        await login(email, password);
      } else {
        await register(email, password, fullName);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={S.root}>
      <div style={S.ambient} />
      <div style={S.card}>
        <div style={S.logoRow}>
          <div style={S.logoBox}><LogoIcon /></div>
          <span style={S.logoText}>ProcureAI</span>
        </div>
        <p style={S.subtitle}>
          {tab === 'login' ? 'Sign in to your workspace' : 'Create a new account'}
        </p>

        <div style={S.tabs}>
          <button style={S.tabBtn(tab === 'login')} onClick={() => { setTab('login'); setError(''); }}>
            Sign in
          </button>
          <button style={S.tabBtn(tab === 'register')} onClick={() => { setTab('register'); setError(''); }}>
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {tab === 'register' && (
            <>
              <label style={S.label}>Full name</label>
              <input
                style={S.input}
                type="text"
                placeholder="Jane Smith"
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                required
                autoComplete="name"
              />
            </>
          )}
          <label style={S.label}>Email</label>
          <input
            style={S.input}
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <label style={S.label}>Password</label>
          <input
            style={S.input}
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
          />
          <button style={{ ...S.submit, opacity: submitting ? 0.6 : 1 }} type="submit" disabled={submitting}>
            {submitting ? 'Please wait…' : tab === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        {error && <div style={S.error}>{error}</div>}
      </div>
    </div>
  );
}
