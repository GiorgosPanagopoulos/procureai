import { useState, useEffect, useRef } from 'react';
import * as Sentry from '@sentry/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast, Toaster } from 'sonner';
import './App.css';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';

function ErrorFallback({ error }: { error: Error }) {
  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1rem',
      background: 'var(--bg)',
      color: 'var(--text)',
    }}>
      <h2 style={{ margin: 0, color: 'var(--text)' }}>Something went wrong</h2>
      <p style={{ margin: 0, color: 'var(--text2)', fontSize: '0.875rem' }}>{error.message}</p>
      <button
        onClick={() => window.location.reload()}
        style={{
          padding: '0.5rem 1.25rem',
          borderRadius: '6px',
          border: 'none',
          background: 'var(--accent2)',
          color: '#fff',
          cursor: 'pointer',
          fontSize: '0.875rem',
        }}
      >
        Reload
      </button>
    </div>
  );
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface TraceStep {
  type: 'thought' | 'tool_call' | 'observation';
  content?: string;
  tool?: string;
  input?: string;
}

interface UsageInfo {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  cache_creation_tokens?: number;
  cache_read_tokens?: number;
  tool_calls_count?: number;
}

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  toolUsed?: string;
  trace?: TraceStep[];
  usage?: UsageInfo;
  conversationId?: string;
}

interface AgentResponse {
  response: string;
  tool_used?: string;
  conversation_id?: string;
  usage?: UsageInfo;
  trace?: TraceStep[];
}

interface Supplier {
  _id?: string;
  name: string;
  category: string;
  contact: string;
  rating: number;
}

interface Bid {
  _id?: string;
  supplier_id: string;
  items: Array<{ name: string; quantity: number; unit_price: number }>;
  total_price: number;
  delivery_days: number;
  terms: string;
  status: string;
}

// ─── Icon component ───────────────────────────────────────────────────────────
const Icon = ({ name, size = 16, color = 'currentColor' }: { name: string; size?: number; color?: string }) => {
  const icons: Record<string, JSX.Element> = {
    logo:      <svg width={size} height={size} viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="8" height="8" rx="2" fill={color} opacity=".9"/><rect x="13" y="3" width="8" height="8" rx="2" fill={color} opacity=".6"/><rect x="3" y="13" width="8" height="8" rx="2" fill={color} opacity=".6"/><rect x="13" y="13" width="8" height="8" rx="2" fill={color} opacity=".3"/></svg>,
    sun:       <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
    upload:    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
    send:      <svg width={size} height={size} viewBox="0 0 24 24" fill={color}><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>,
    ai:        <svg width={size} height={size} viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.5" opacity=".4"/><circle cx="12" cy="12" r="4" fill={color}/><path d="M12 2v4M12 18v4M2 12h4M18 12h4" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity=".6"/></svg>,
    user:      <svg width={size} height={size} viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" fill={color} opacity=".8"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke={color} strokeWidth="2" strokeLinecap="round" fill="none" opacity=".6"/></svg>,
    suppliers: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9,22 9,12 15,12 15,22"/></svg>,
    bids:      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>,
    chart:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
    check:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>,
    sparkle:   <svg width={size} height={size} viewBox="0 0 24 24" fill={color}><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/></svg>,
    close:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
    refresh:   <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>,
    search:    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
    globe:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>,
    brain:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><path d="M9.5 2a2.5 2.5 0 014.8.9A3 3 0 0117 6a3 3 0 01-1.5 2.6A3 3 0 0118 11a3 3 0 01-2.5 3A2.5 2.5 0 0114 16.5V22"/><path d="M9.5 2a2.5 2.5 0 00-4.8.9A3 3 0 006 6a3 3 0 001.5 2.6A3 3 0 006 11a3 3 0 002.5 3A2.5 2.5 0 0110 16.5V22"/></svg>,
  };
  return icons[name] ?? null;
};

// ─── Shared components ────────────────────────────────────────────────────────
function StarRating({ rating }: { rating: number }) {
  return (
    <span>
      {Array.from({ length: 5 }).map((_, i) => (
        <span key={i} className={i < Math.round(rating) ? 'star-filled' : 'star-empty'}>★</span>
      ))}
    </span>
  );
}

function StatusPill({ status }: { status: string }) {
  const s = status.toLowerCase();
  const cls = s === 'accepted' ? 'status-pill status-pill-accepted'
            : s === 'rejected' ? 'status-pill status-pill-rejected'
            :                    'status-pill status-pill-pending';
  return <span className={cls}>{status}</span>;
}

const TypingDots = () => (
  <div className="typing-dots">
    {[0, 1, 2].map(i => (
      <div key={i} className="typing-dot" style={{ animationDelay: `${i * 0.2}s` }} />
    ))}
  </div>
);

// ─── Trace panel ─────────────────────────────────────────────────────────────
const STEP_META: Record<TraceStep['type'], { icon: string; label_en: string; label_gr: string }> = {
  thought:     { icon: '🤔', label_en: 'Thought',      label_gr: 'Σκέψη' },
  tool_call:   { icon: '🔧', label_en: 'Tool call',    label_gr: 'Κλήση εργαλείου' },
  observation: { icon: '📋', label_en: 'Observation',  label_gr: 'Παρατήρηση' },
};

function TracePanel({ trace, lang, viewLabel, hideLabel }: {
  trace: TraceStep[];
  lang: 'en' | 'gr';
  viewLabel: string;
  hideLabel: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="trace-panel">
      <button className="trace-toggle" onClick={() => setOpen(p => !p)}>
        <span className="trace-toggle-icon">{open ? '▲' : '▼'}</span>
        {open ? hideLabel : viewLabel}
      </button>
      {open && (
        <div className="trace-steps">
          {trace.map((step, i) => {
            const meta = STEP_META[step.type];
            const label = lang === 'gr' ? meta.label_gr : meta.label_en;
            const body = step.type === 'tool_call'
              ? `${step.tool}(${step.input ?? ''})`
              : (step.content ?? '');
            return (
              <div key={i} className={`trace-step trace-step-${step.type}`}>
                <span className="trace-step-icon">{meta.icon}</span>
                <div className="trace-step-body">
                  <span className="trace-step-label">{label}</span>
                  <p className="trace-step-text">{body}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Usage badge ─────────────────────────────────────────────────────────────
function UsageBadge({ usage }: { usage: UsageInfo }) {
  const tooltip = [
    `Input: ${usage.input_tokens} tokens`,
    `Output: ${usage.output_tokens} tokens`,
    usage.cache_creation_tokens ? `Cache write: ${usage.cache_creation_tokens}` : '',
    usage.cache_read_tokens     ? `Cache read: ${usage.cache_read_tokens}` : '',
  ].filter(Boolean).join(' · ');

  return (
    <div className="usage-badge" title={tooltip}>
      ↑{usage.input_tokens} ↓{usage.output_tokens} · ${usage.cost_usd.toFixed(4)}
    </div>
  );
}

// ─── Suggestion data ──────────────────────────────────────────────────────────
const SUGGESTIONS = {
  en: [
    { label: 'Compare bids for office equipment', icon: 'chart' },
    { label: 'Find suppliers for IT hardware',    icon: 'search' },
    { label: 'Generate procurement report',       icon: 'bids' },
    { label: 'Payment terms in contracts',        icon: 'check' },
    { label: 'Show medical equipment bids',       icon: 'sparkle' },
    { label: 'Find high-rated suppliers',         icon: 'suppliers' },
  ],
  gr: [
    { label: 'Σύγκριση προσφορών εξοπλισμού',    icon: 'chart' },
    { label: 'Εύρεση προμηθευτών IT',             icon: 'search' },
    { label: 'Δημιουργία αναφοράς προμηθειών',   icon: 'bids' },
    { label: 'Όροι πληρωμής στα συμβόλαια',      icon: 'check' },
    { label: 'Προσφορές ιατρικού εξοπλισμού',    icon: 'sparkle' },
    { label: 'Εύρεση κορυφαίων προμηθευτών',     icon: 'suppliers' },
  ],
};

const TRANSLATIONS = {
  en: {
    connected: 'Connected', disconnected: 'Disconnected',
    welcome: 'Welcome to ProcureAI',
    welcomeDesc: 'Ask me anything about procurement, bids, suppliers, or contracts. I have access to your full database.',
    placeholder: 'Ask about procurement, bids, suppliers…',
    dataInspector: 'Data Inspector', results: 'Results',
    agentResponses: 'Agent Responses',
    noResults: 'No results yet',
    noResultsDesc: 'Start a conversation to see AI responses here',
    viewReasoning: 'View reasoning',
    hideReasoning: 'Hide reasoning',
  },
  gr: {
    connected: 'Συνδεδεμένο', disconnected: 'Αποσυνδεδεμένο',
    welcome: 'Καλώς ήρθατε στο ProcureAI',
    welcomeDesc: 'Ρωτήστε με οτιδήποτε για προμήθειες, προσφορές, προμηθευτές ή συμβάσεις.',
    placeholder: 'Ρωτήστε για προμήθειες, προσφορές, προμηθευτές…',
    dataInspector: 'Επισκόπηση', results: 'Αποτελέσματα',
    agentResponses: 'Απαντήσεις',
    noResults: 'Δεν υπάρχουν αποτελέσματα',
    noResultsDesc: 'Ξεκινήστε μια συζήτηση για να δείτε απαντήσεις εδώ',
    viewReasoning: 'Εμφάνιση λογικής',
    hideReasoning: 'Απόκρυψη λογικής',
  },
};

// ─── App ──────────────────────────────────────────────────────────────────────
function AppContent() {
  const [messages, setMessages]       = useState<Message[]>([]);
  const [inputValue, setInputValue]   = useState('');
  const [isLoading, setIsLoading]     = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const chatRef    = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [bids, setBids]           = useState<Bid[]>([]);
  const [rightTab, setRightTab]   = useState<'data' | 'results'>('data');
  const [loadingData, setLoadingData] = useState<'suppliers' | 'bids' | null>(null);
  const [showMoreSuppliers, setShowMoreSuppliers] = useState(false);
  const [showMoreBids, setShowMoreBids]           = useState(false);

  const [isDark, setIsDark] = useState<boolean>(() =>
    localStorage.getItem('darkMode') !== 'false'
  );
  const [language, setLanguage] = useState<'en' | 'gr'>(() =>
    localStorage.getItem('language') === 'gr' ? 'gr' : 'en'
  );
  const [isDragging, setIsDragging]     = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const agentMessages = messages.filter(m => m.sender === 'agent');
  const t = TRANSLATIONS[language];
  const suggestions = SUGGESTIONS[language];

  useEffect(() => {
    if (chatRef.current)
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => { localStorage.setItem('darkMode', String(isDark)); }, [isDark]);
  useEffect(() => { localStorage.setItem('language', language); }, [language]);

  const fetchWithTimeout = async (input: RequestInfo, init?: RequestInit, timeout = 15000) => {
    const ctrl = new AbortController();
    const id = setTimeout(() => ctrl.abort(), timeout);
    try {
      return await fetch(input, { ...init, signal: ctrl.signal, credentials: 'include' as RequestCredentials });
    } finally {
      clearTimeout(id);
    }
  };

  useEffect(() => {
    const check = async () => {
      try { setIsConnected((await fetch('http://localhost:8000/')).ok); }
      catch { setIsConnected(false); }
    };
    check();
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, []);

  const handleSubmit = async (text?: string) => {
    const txt = (text ?? inputValue).trim();
    if (!txt || isLoading) return;
    setInputValue('');

    const userMsg: Message = { id: Date.now().toString(), text: txt, sender: 'user', timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await fetchWithTimeout('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: txt }),
      }, 60000);

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || res.statusText || 'Request failed');
      }

      const data: AgentResponse = await res.json();
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        text: data.response?.trim() || 'No answer returned.',
        sender: 'agent',
        timestamp: new Date(),
        toolUsed: data.tool_used,
        trace: data.trace,
        usage: data.usage,
        conversationId: data.conversation_id,
      }]);
      setRightTab('results');
    } catch (err) {
      Sentry.captureException(err, { tags: { component: 'chat' }, extra: { query: txt } });
      const raw = err instanceof Error ? err.message : 'Unknown error';
      const isNetwork = raw === 'Load failed' || raw === 'Failed to fetch';
      const isTimeout = raw.includes('abort') || raw.includes('AbortError');
      const friendly = isNetwork
        ? 'Could not reach the backend. Make sure the server is running on port 8000.'
        : isTimeout
        ? 'The request timed out. The agent is taking too long — try a simpler query.'
        : `Error: ${raw}`;
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        text: friendly,
        sender: 'agent',
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const processFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    setIsLoading(true);
    try {
      const res = await fetchWithTimeout('http://localhost:8000/upload', { method: 'POST', body: formData }, 20000);
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || 'Upload failed');
      }
      const result = await res.json();
      setUploadedFile(file);
      toast.success(`Uploaded "${file.name}" successfully`);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        text: `Successfully uploaded ${file.name}. ${result.message || 'Document processed and ready for queries.'}`,
        sender: 'agent',
        timestamp: new Date(),
      }]);
    } catch (err) {
      Sentry.captureException(err, { tags: { component: 'upload' }, extra: { filename: file.name } });
      toast.error(`Upload failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    if (file.type !== 'application/pdf') { toast.error('Please upload a PDF file'); return; }
    processFile(file);
  };

  const handleLoadSuppliers = async () => {
    setLoadingData('suppliers');
    try {
      const res = await fetchWithTimeout('http://localhost:8000/suppliers', undefined, 15000);
      if (!res.ok) throw new Error('Failed to fetch suppliers');
      const data = await res.json();
      setSuppliers(data);
      toast.success(`Loaded ${data.length} suppliers`);
    } catch (err) {
      Sentry.captureException(err, { tags: { component: 'chat' } });
      toast.error(err instanceof Error ? err.message : 'Failed to load suppliers');
    } finally {
      setLoadingData(null);
    }
  };

  const handleLoadBids = async () => {
    setLoadingData('bids');
    try {
      const res = await fetchWithTimeout('http://localhost:8000/bids', undefined, 15000);
      if (!res.ok) throw new Error('Failed to fetch bids');
      const data = await res.json();
      setBids(data);
      toast.success(`Loaded ${data.length} bids`);
    } catch (err) {
      Sentry.captureException(err, { tags: { component: 'chat' } });
      toast.error(err instanceof Error ? err.message : 'Failed to load bids');
    } finally {
      setLoadingData(null);
    }
  };

  const avgBidValue = bids.length > 0
    ? (bids.reduce((s, b) => s + b.total_price, 0) / bids.length)
        .toLocaleString('en-US', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
    : '—';
  const activeBids = bids.filter(b => b.status.toLowerCase() === 'pending').length;

  const visibleSuppliers = showMoreSuppliers ? suppliers : suppliers.slice(0, 5);
  const visibleBids      = showMoreBids      ? bids      : bids.slice(0, 5);

  const { user, isLoading: authLoading, logout } = useAuth();
  if (authLoading) return <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', color: 'var(--text)' }}>Loading...</div>;
  if (!user) return <LoginPage />;

  return (
    <div className={`app-root${isDark ? '' : ' light'}`}>
      <Toaster position="bottom-right" theme="dark" />
      <div className="ambient-bg" />

      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-left">
          <div className="logo-box">
            <Icon name="logo" size={16} color="var(--accent2)" />
          </div>
          <span className="logo-text">ProcureAI</span>
          <span className="beta-badge">BETA</span>
        </div>
        <div className="header-right">
          <button
            className="header-btn"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            onClick={() => setIsDark(p => !p)}
          >
            {isDark ? (
              <Icon name="sun" size={14} color="var(--text2)" />
            ) : (
              <svg width={14} height={14} viewBox="0 0 24 24" fill="var(--text2)">
                <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"/>
              </svg>
            )}
          </button>
          <button
            className="header-btn lang"
            onClick={() => setLanguage(p => p === 'en' ? 'gr' : 'en')}
            title="Switch language"
          >
            <Icon name="globe" size={13} color="var(--text2)" />
            {language.toUpperCase()}
          </button>
          <button className="header-btn" title="Logout" onClick={logout}>
            <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="var(--text2)" strokeWidth="2" strokeLinecap="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
          <div className={`connection-badge ${isConnected ? 'connected' : 'disconnected'}`}>
            <div className="pulse-dot" />
            {isConnected ? t.connected : t.disconnected}
          </div>
        </div>
      </header>

      {/* ── Main ── */}
      <div className="app-main">

        {/* ── Left: Chat ── */}
        <div className="chat-panel">

          {/* Messages */}
          <div className="chat-messages" ref={chatRef}>
            {messages.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <Icon name="ai" size={26} color="var(--accent2)" />
                </div>
                <h2 className="empty-title">{t.welcome}</h2>
                <p className="empty-desc">{t.welcomeDesc}</p>
                <div className="empty-pills">
                  <div className="empty-pill" style={{ color: 'var(--cyan)' }}>
                    {suppliers.length || 128} Suppliers
                  </div>
                  <div className="empty-pill" style={{ color: '#a78bfa' }}>
                    {bids.length || 47} Active Bids
                  </div>
                  <div className="empty-pill" style={{ color: 'var(--accent2)' }}>
                    €2.4M Pipeline
                  </div>
                </div>
              </div>
            ) : (
              <>
                {messages.map(msg => (
                  <div key={msg.id} className={`msg-row ${msg.sender}`}>
                    <div className={`msg-avatar ${msg.sender}`}>
                      <Icon
                        name={msg.sender === 'agent' ? 'ai' : 'user'}
                        size={14}
                        color={msg.sender === 'agent' ? 'var(--accent2)' : 'var(--text2)'}
                      />
                    </div>
                    <div className="msg-content">
                      <div className={`msg-bubble ${msg.sender}`}>
                        {msg.sender === 'agent' ? (
                          <div className="prose-agent">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                          </div>
                        ) : (
                          msg.text
                        )}
                        {msg.toolUsed && (
                          <div className="tool-badge">⚙ {msg.toolUsed}</div>
                        )}
                        {msg.usage && <UsageBadge usage={msg.usage} />}
                      </div>
                      {msg.trace && msg.trace.length > 0 && (
                        <TracePanel
                          trace={msg.trace}
                          lang={language}
                          viewLabel={t.viewReasoning}
                          hideLabel={t.hideReasoning}
                        />
                      )}
                      <div className="msg-time">
                        {msg.timestamp.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="msg-row agent">
                    <div className="msg-avatar agent">
                      <Icon name="ai" size={14} color="var(--accent2)" />
                    </div>
                    <div className="msg-content">
                      <div className="msg-bubble agent">
                        <TypingDots />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Suggestions */}
          <div className="suggestions-strip">
            {suggestions.map((s, i) => (
              <button key={i} className="suggestion-chip" onClick={() => handleSubmit(s.label)}>
                <Icon name={s.icon} size={11} color="var(--accent2)" />
                {s.label}
              </button>
            ))}
          </div>

          {/* Upload strip */}
          <div className="upload-strip">
            {uploadedFile ? (
              <div className="upload-confirmed">
                <Icon name="bids" size={14} color="var(--cyan)" />
                <span className="upload-filename">{uploadedFile.name}</span>
                <button className="upload-clear" onClick={() => setUploadedFile(null)}>
                  <Icon name="close" size={12} color="var(--text3)" />
                </button>
              </div>
            ) : (
              <div
                className={`drop-zone ${isDragging ? 'dragover' : ''}`}
                onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <Icon name="upload" size={14} color={isDragging ? 'var(--accent2)' : 'var(--text3)'} />
                <span>
                  Drag &amp; drop PDF, or{' '}
                  <span className="upload-link">click to upload</span>
                </span>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              style={{ display: 'none' }}
              onChange={e => { const f = e.target.files?.[0]; if (f) processFile(f); }}
            />
          </div>

          {/* Input bar */}
          <div className="input-area">
            <div className="input-bar">
              <input
                className="chat-input"
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
                placeholder={t.placeholder}
                disabled={isLoading}
              />
              <button
                className={`send-btn ${inputValue.trim() ? 'active' : ''}`}
                onClick={() => handleSubmit()}
                disabled={isLoading || !inputValue.trim()}
              >
                <Icon name="send" size={14} color={inputValue.trim() ? '#fff' : 'var(--text3)'} />
              </button>
            </div>
          </div>
        </div>

        {/* ── Right: Data panel ── */}
        <div className="right-panel">

          {/* Tabs */}
          <div className="tab-bar">
            {([
              { id: 'data',    label: t.dataInspector, icon: 'suppliers' },
              { id: 'results', label: t.results,        icon: 'chart' },
            ] as const).map(tab => (
              <button
                key={tab.id}
                className={`tab-btn ${rightTab === tab.id ? 'active' : ''}`}
                onClick={() => setRightTab(tab.id)}
              >
                <Icon name={tab.icon} size={13} color={rightTab === tab.id ? 'var(--accent2)' : 'var(--text3)'} />
                {tab.label}
                {tab.id === 'results' && agentMessages.length > 0 && (
                  <span className="tab-badge">{agentMessages.length}</span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="tab-content">
            {rightTab === 'data' ? (
              <>
                <p className="section-label">Database Records</p>

                {/* Count cards */}
                <div className="data-cards-grid">
                  {([
                    { type: 'suppliers' as const, icon: 'suppliers', label: 'Suppliers', count: suppliers.length, color: '#22d3ee', rgb: '34,211,238', load: handleLoadSuppliers },
                    { type: 'bids'      as const, icon: 'bids',      label: 'Bids',      count: bids.length,      color: '#a78bfa', rgb: '167,139,250', load: handleLoadBids },
                  ]).map(({ type, icon, label, count, color, rgb, load }) => (
                    <button
                      key={type}
                      className="count-card"
                      style={{
                        background: count > 0 ? `rgba(${rgb},0.08)` : 'var(--surface3)',
                        border: `1px solid ${count > 0 ? `rgba(${rgb},0.25)` : 'var(--border)'}`,
                      }}
                      onClick={load}
                    >
                      {loadingData === type && (
                        <div className="card-loading-overlay">
                          <div className="card-spinner" style={{ borderColor: color, borderTopColor: 'transparent' }} />
                        </div>
                      )}
                      <div className="count-card-header">
                        <Icon name={icon} size={14} color={color} />
                        <span className="count-card-label" style={{ color: count > 0 ? color : 'var(--text2)' }}>{label}</span>
                      </div>
                      <div className="count-card-value" style={{ color: count > 0 ? 'var(--text)' : 'var(--text3)' }}>{count}</div>
                      <div className="count-card-sub">{count === 0 ? 'Click to load' : 'records loaded'}</div>
                    </button>
                  ))}
                </div>

                {(suppliers.length > 0 || bids.length > 0) && (
                  <div className="data-loaded-badge">
                    <Icon name="check" size={12} color="var(--success)" />
                    Data loaded · Last sync: just now
                  </div>
                )}

                {/* Quick stats */}
                {bids.length > 0 && (
                  <div className="quick-stats">
                    <p className="section-label">Quick Stats</p>
                    {[
                      { label: 'Avg bid value',  value: avgBidValue,          trend: '+8%', pos: true },
                      { label: 'Active bids',    value: String(activeBids),   trend: `+${activeBids}`, pos: true },
                      { label: 'Total bids',     value: String(bids.length),  trend: '' },
                    ].map(s => (
                      <div key={s.label} className="stat-row">
                        <span className="stat-label">{s.label}</span>
                        <div className="stat-value-group">
                          <span className="stat-value">{s.value}</span>
                          {s.trend && (
                            <span className={`stat-trend ${s.pos ? 'positive' : 'warning'}`}>{s.trend}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Supplier list */}
                {suppliers.length > 0 && (
                  <div className="data-section">
                    <p className="section-label">Suppliers ({suppliers.length})</p>
                    <div className="data-list">
                      {visibleSuppliers.map((s, i) => (
                        <div key={i} className="data-item">
                          <div className="data-item-row">
                            <span className="data-item-name">{s.name}</span>
                            <span className="category-badge">{s.category}</span>
                          </div>
                          <div className="data-item-row">
                            <StarRating rating={s.rating} />
                            <span className="data-item-sub">{s.contact}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                    {suppliers.length > 5 && (
                      <button className="show-more-btn" onClick={() => setShowMoreSuppliers(p => !p)}>
                        {showMoreSuppliers ? 'Show less' : `Show ${suppliers.length - 5} more`}
                      </button>
                    )}
                  </div>
                )}

                {/* Bid list */}
                {bids.length > 0 && (
                  <div className="data-section">
                    <p className="section-label">Bids ({bids.length})</p>
                    <div className="data-list">
                      {visibleBids.map((b, i) => (
                        <div key={i} className="data-item">
                          <div className="data-item-row">
                            <span className="data-item-sub">
                              Supplier: <span style={{ color: 'var(--text)' }}>{b.supplier_id}</span>
                            </span>
                            <StatusPill status={b.status} />
                          </div>
                          <div className="data-item-row">
                            <span className="data-item-price">
                              {b.total_price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                            </span>
                            <span className="data-item-sub">{b.delivery_days}d delivery</span>
                          </div>
                        </div>
                      ))}
                    </div>
                    {bids.length > 5 && (
                      <button className="show-more-btn" onClick={() => setShowMoreBids(p => !p)}>
                        {showMoreBids ? 'Show less' : `Show ${bids.length - 5} more`}
                      </button>
                    )}
                  </div>
                )}
              </>
            ) : (
              <>
                <p className="section-label">{t.agentResponses}</p>
                {agentMessages.length === 0 ? (
                  <div className="results-empty">
                    <Icon name="chart" size={32} color="var(--text3)" />
                    <p className="results-empty-title">{t.noResults}</p>
                    <p className="results-empty-desc">{t.noResultsDesc}</p>
                  </div>
                ) : (
                  <div className="results-list">
                    {[...agentMessages].reverse().map((msg, i) => (
                      <div key={msg.id} className="result-card" style={{ animationDelay: `${i * 60}ms` }}>
                        <div className="result-card-header">
                          <span className="result-card-type">Query Result</span>
                          <span className="result-card-time">
                            {msg.timestamp.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <div className="result-card-body">
                          {msg.text.length > 160 ? msg.text.slice(0, 157) + '…' : msg.text}
                        </div>
                        <div className="result-card-tags">
                          <span className="result-tag">Procurement</span>
                          {msg.toolUsed && <span className="result-tag">{msg.toolUsed}</span>}
                          {msg.usage && (
                            <span className="result-tag">${msg.usage.cost_usd.toFixed(4)}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div className="panel-footer">
            <div className="footer-stats">
              <span className="footer-dot">●</span> {suppliers.length} suppliers · {bids.length} bids
            </div>
            <button className="footer-clear-btn" onClick={() => setMessages([])}>
              <Icon name="refresh" size={11} color="currentColor" /> Clear
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <Sentry.ErrorBoundary fallback={({ error }) => <ErrorFallback error={error as Error} />}>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Sentry.ErrorBoundary>
  );
}

export default App;
