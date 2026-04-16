import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast, Toaster } from 'sonner';
import './App.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  toolUsed?: string;
}

interface AgentResponse {
  response: string;
  tool_used?: string;
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
  const cls =
    s === 'accepted' ? 'status-pill status-pill-accepted' :
    s === 'rejected' ? 'status-pill status-pill-rejected' :
                       'status-pill status-pill-pending';
  return <span className={cls}>{status}</span>;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [bids, setBids] = useState<Bid[]>([]);
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    const stored = localStorage.getItem('darkMode');
    if (stored === 'true') return true;
    if (stored === 'false') return false;
    return false;
  });

  const [language, setLanguage] = useState<'en' | 'gr'>(() => {
    if (typeof window === 'undefined') return 'en';
    const stored = localStorage.getItem('language');
    return stored === 'gr' ? 'gr' : 'en';
  });

  // UI-only state
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [showMoreSuppliers, setShowMoreSuppliers] = useState(false);
  const [showMoreBids, setShowMoreBids] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('darkMode', String(isDarkMode));
  }, [isDarkMode]);

  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  const fetchWithTimeout = async (input: RequestInfo, init?: RequestInit, timeout = 15000) => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(input, { ...init, signal: controller.signal });
      return response;
    } finally {
      clearTimeout(id);
    }
  };

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch('http://localhost:8000/');
        setIsConnected(response.ok);
      } catch {
        setIsConnected(false);
      }
    };
    checkConnection();
    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetchWithTimeout('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage.text }),
      }, 20000);

      if (!response) throw new Error('No response from server');

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => null);
        const errorMessage = errorPayload?.detail || response.statusText || 'Unknown error';
        throw new Error(`Agent request failed: ${errorMessage}`);
      }

      const data: AgentResponse = await response.json();
      const agentText = data.response?.trim() || 'Agent returned no answer. Please try again.';

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: agentText,
        sender: 'agent',
        timestamp: new Date(),
        toolUsed: data.tool_used,
      };

      setMessages(prev => [...prev, agentMessage]);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error occurred';
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `Error: ${message}`,
        sender: 'agent',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const processFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    setIsLoading(true);
    try {
      const response = await fetchWithTimeout('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      }, 20000);

      if (!response) throw new Error('No response from upload endpoint');

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => null);
        const msg = errorPayload?.detail || response.statusText || 'Upload failed';
        throw new Error(`Failed to upload file: ${msg}`);
      }

      const result = await response.json();
      setUploadedFileName(file.name);
      toast.success(`Uploaded "${file.name}" successfully`);

      const uploadMessage: Message = {
        id: Date.now().toString(),
        text: `Successfully uploaded ${file.name}. ${result.message || 'Document processed and ready for queries.'}`,
        sender: 'agent',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, uploadMessage]);
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Unknown error';
      toast.error(`Upload failed: ${msg}`);
      const errorMessage: Message = {
        id: Date.now().toString(),
        text: `Upload failed: ${msg}`,
        sender: 'agent',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    processFile(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    if (file.type !== 'application/pdf') {
      toast.error('Please upload a PDF file');
      return;
    }
    processFile(file);
  };

  const translations = {
    en: {
      connected: 'Connected',
      disconnected: 'Disconnected',
      welcome: 'Welcome to ProcureAI!',
      welcomeDesc: 'Ask me anything about procurement, bids, suppliers, or contracts.',
      placeholder: 'Ask about procurement, bids, suppliers...',
      dataInspector: 'Data Inspector',
      loadSuppliers: 'Load Suppliers',
      loadBids: 'Load Bids',
      results: 'Results',
      agentResponses: 'Agent responses will appear here',
      agentResponsesDesc: 'Try asking about bids, suppliers, or contracts',
      send: 'Send',
      suggestionChips: [
        'Compare bids for office equipment',
        'Find suppliers for IT hardware',
        'Generate procurement report',
        'What are payment terms in contracts?',
        'Show me medical equipment bids',
        'Find high-rated suppliers',
      ],
    },
    gr: {
      connected: 'Συνδεδεμένο',
      disconnected: 'Αποσυνδεδεμένο',
      welcome: 'Καλώς ήρθατε στο ProcureAI!',
      welcomeDesc: 'Ρωτήστε με οτιδήποτε για προμήθειες, προσφορές, προμηθευτές ή συμβάσεις.',
      placeholder: 'Ρωτήστε για προμήθειες, προσφορές, προμηθευτές...',
      dataInspector: 'Επισκόπηση Δεδομένων',
      loadSuppliers: 'Φόρτωση Προμηθευτών',
      loadBids: 'Φόρτωση Προσφορών',
      results: 'Αποτελέσματα',
      agentResponses: 'Οι απαντήσεις του agent θα εμφανιστούν εδώ',
      agentResponsesDesc: 'Δοκιμάστε να ρωτήσετε για προσφορές, προμηθευτές ή συμβάσεις',
      send: 'Αποστολή',
      suggestionChips: [
        'Σύγκριση προσφορών εξοπλισμού',
        'Εύρεση προμηθευτών IT',
        'Δημιουργία αναφοράς προμηθειών',
        'Όροι πληρωμής στα συμβόλαια;',
        'Προσφορές ιατρικού εξοπλισμού',
        'Εύρεση κορυφαίων προμηθευτών',
      ],
    },
  };

  const t = translations[language];

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
  };

  const handleLoadSuppliers = async () => {
    try {
      const response = await fetchWithTimeout('http://localhost:8000/suppliers', undefined, 15000);
      if (!response || !response.ok) throw new Error('Failed to fetch suppliers');
      const data = await response.json();
      setSuppliers(data);
      toast.success(`Loaded ${data.length} suppliers`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load suppliers');
    }
  };

  const handleLoadBids = async () => {
    try {
      const response = await fetchWithTimeout('http://localhost:8000/bids', undefined, 15000);
      if (!response || !response.ok) throw new Error('Failed to fetch bids');
      const data = await response.json();
      setBids(data);
      toast.success(`Loaded ${data.length} bids`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load bids');
    }
  };

  const visibleSuppliers = showMoreSuppliers ? suppliers : suppliers.slice(0, 5);
  const visibleBids = showMoreBids ? bids : bids.slice(0, 5);

  return (
    <div className="h-screen flex flex-col dot-grid">
      <Toaster position="bottom-right" theme={isDarkMode ? 'dark' : 'light'} />

      {/* ── Header ── */}
      <header className="header-glass px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold shimmer-title">ProcureAI</h1>
          <div className="flex items-center gap-3">
            {/* Dark mode toggle */}
            <button
              onClick={() => setIsDarkMode(prev => !prev)}
              className="icon-btn"
              title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDarkMode ? (
                <svg className="w-5 h-5" style={{ color: '#f59e0b' }} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-5 h-5" style={{ color: 'var(--text-secondary)' }} fill="currentColor" viewBox="0 0 20 20">
                  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                </svg>
              )}
            </button>

            {/* Language toggle */}
            <button
              onClick={() => setLanguage(prev => prev === 'en' ? 'gr' : 'en')}
              className="lang-btn"
              title={`Switch to ${language === 'en' ? 'Greek' : 'English'}`}
            >
              {language.toUpperCase()}
            </button>

            {/* Connection status */}
            <div className="flex items-center gap-2">
              <div className={`status-dot ${isConnected ? 'status-dot-connected' : 'status-dot-disconnected'}`} />
              <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                {isConnected ? t.connected : t.disconnected}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <div className="flex-1 flex overflow-hidden p-3 gap-3">

        {/* ── Left Panel — Chat ── */}
        <div className="w-full lg:w-1/2 flex flex-col panel-glass overflow-hidden">

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center mt-10 space-y-2">
                <p className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>{t.welcome}</p>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{t.welcomeDesc}</p>
              </div>
            )}

            {messages.map(message => (
              <div
                key={message.id}
                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.sender === 'agent' ? (
                  <div>
                    <div className="agent-sender-label">ProcureAI</div>
                    <div className="bubble-agent">
                      <div className="prose-agent">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.text}
                        </ReactMarkdown>
                      </div>
                      {message.toolUsed && (
                        <div className="tool-badge">⚙ {message.toolUsed}</div>
                      )}
                      <div className="bubble-timestamp">{message.timestamp.toLocaleTimeString()}</div>
                    </div>
                  </div>
                ) : (
                  <div className="bubble-user">
                    <p className="text-sm">{message.text}</p>
                    <div className="bubble-timestamp">{message.timestamp.toLocaleTimeString()}</div>
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div>
                  <div className="agent-sender-label">ProcureAI</div>
                  <div className="bubble-agent">
                    <div className="flex items-center gap-1" style={{ padding: '2px 0' }}>
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 space-y-3" style={{ borderTop: '1px solid var(--border-color)' }}>

            {/* Drop Zone */}
            <div
              className={`drop-zone ${isDragging ? 'dragover' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <svg
                className="mx-auto mb-2"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#0ea5e9"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              {uploadedFileName ? (
                <p className="text-sm font-medium" style={{ color: '#0ea5e9' }}>
                  {uploadedFileName}
                </p>
              ) : (
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Drag &amp; drop PDF here, or <span style={{ color: '#0ea5e9' }}>click to upload</span>
                </p>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileInputChange}
                style={{ display: 'none' }}
              />
            </div>

            {/* Suggestion Chips */}
            <div className="flex flex-wrap gap-2">
              {t.suggestionChips.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="suggestion-chip"
                >
                  {suggestion}
                </button>
              ))}
            </div>

            {/* Message Input */}
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                placeholder={t.placeholder}
                className="chat-input"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !inputValue.trim()}
                className="btn-send"
              >
                {t.send}
              </button>
            </form>
          </div>
        </div>

        {/* ── Right Panel — Data Inspector ── */}
        <div className="w-full lg:w-1/2 flex flex-col gap-3 overflow-y-auto">

          {/* Data Inspector Card */}
          <div className="panel-glass p-5">
            <h2 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
              {t.dataInspector}
            </h2>

            <div className="flex flex-wrap gap-2 mb-4">
              <button onClick={handleLoadSuppliers} className="btn-outlined">{t.loadSuppliers}</button>
              <button onClick={handleLoadBids} className="btn-outlined">{t.loadBids}</button>
            </div>

            <p className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>
              Suppliers: {suppliers.length} &nbsp;·&nbsp; Bids: {bids.length}
            </p>

            {/* Supplier Cards */}
            {suppliers.length > 0 && (
              <div className="mb-4">
                <p className="section-label">Suppliers ({suppliers.length})</p>
                <div className="space-y-2">
                  {visibleSuppliers.map((s, idx) => (
                    <div key={idx} className="data-card">
                      <div className="flex items-center justify-between flex-wrap gap-1 mb-1">
                        <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{s.name}</span>
                        <span className="category-badge">{s.category}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <StarRating rating={s.rating} />
                        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{s.contact}</span>
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

            {/* Bid Cards */}
            {bids.length > 0 && (
              <div>
                <p className="section-label">Bids ({bids.length})</p>
                <div className="space-y-2">
                  {visibleBids.map((b, idx) => (
                    <div key={idx} className="data-card">
                      <div className="flex items-center justify-between flex-wrap gap-1 mb-1">
                        <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                          Supplier: <span style={{ color: 'var(--text-primary)' }}>{b.supplier_id}</span>
                        </span>
                        <StatusPill status={b.status} />
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold" style={{ color: '#0ea5e9' }}>
                          {b.total_price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                        </span>
                        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {b.delivery_days}d delivery
                        </span>
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
          </div>

          {/* Results Card */}
          <div className="panel-glass p-5 flex-1">
            <h2 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
              {t.results}
            </h2>

            {messages.filter(m => m.sender === 'agent').length === 0 ? (
              <div className="text-center py-8 space-y-1">
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{t.agentResponses}</p>
                <p className="text-xs" style={{ color: 'var(--text-secondary)', opacity: 0.7 }}>{t.agentResponsesDesc}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {messages
                  .filter(msg => msg.sender === 'agent')
                  .slice(-3)
                  .map(message => (
                    <div key={message.id} className="data-card">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <span className="text-xs font-semibold" style={{ color: '#0ea5e9' }}>ProcureAI</span>
                        {message.toolUsed && (
                          <span className="tool-badge">⚙ {message.toolUsed}</span>
                        )}
                      </div>
                      <div
                        className="prose-agent"
                        style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: '0.78rem',
                          lineHeight: '1.6',
                          color: 'var(--text-primary)',
                        }}
                      >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.text}
                        </ReactMarkdown>
                      </div>
                      <p className="bubble-timestamp">{message.timestamp.toLocaleString()}</p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
