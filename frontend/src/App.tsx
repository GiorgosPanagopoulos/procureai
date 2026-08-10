import { useState } from 'react';
import * as Sentry from '@sentry/react';
import { Toaster } from 'sonner';
import './App.css';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import ErrorFallback from './components/common/ErrorFallback';
import Header from './components/layout/Header';
import ChatPanel from './components/chat/ChatPanel';
import DataInspector from './components/inspector/DataInspector';
import { useChat } from './hooks/useChat';
import { useTheme } from './hooks/useTheme';
import { useI18n } from './hooks/useI18n';
import { useCatalogData } from './hooks/useCatalogData';
import type { RightTab } from './types';

function AppContent() {
  const { user, isLoading: authLoading, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const { language, toggleLanguage, t, suggestions } = useI18n();
  const catalog = useCatalogData();
  const [rightTab, setRightTab] = useState<RightTab>('data');
  const chat = useChat({ onMessageReceived: () => setRightTab('results') });

  if (authLoading) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', color: 'var(--text)' }}>
        Loading...
      </div>
    );
  }
  if (!user) return <LoginPage />;

  return (
    <div className={`app-root${isDark ? '' : ' light'}`}>
      <Toaster position="bottom-right" theme="dark" />
      <div className="ambient-bg" />

      <Header
        isDark={isDark}
        onToggleTheme={toggleTheme}
        language={language}
        onToggleLanguage={toggleLanguage}
        isConnected={chat.isConnected}
        connectedLabel={t.connected}
        disconnectedLabel={t.disconnected}
        onLogout={logout}
      />

      <div className="app-main">
        <ChatPanel
          chat={chat}
          language={language}
          t={t}
          suggestions={suggestions}
          suppliersCount={catalog.suppliers.length}
          bidsCount={catalog.bids.length}
        />
        <DataInspector
          messages={chat.messages}
          suppliers={catalog.suppliers}
          bids={catalog.bids}
          loadingData={catalog.loadingData}
          onLoadSuppliers={catalog.loadSuppliers}
          onLoadBids={catalog.loadBids}
          rightTab={rightTab}
          onTabChange={setRightTab}
          onClearChat={chat.clearChat}
          t={t}
        />
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
