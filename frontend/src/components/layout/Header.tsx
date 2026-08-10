import Icon from '../common/Icon';
import ThemeToggle from './ThemeToggle';
import LanguageToggle from './LanguageToggle';
import type { Language } from '../../types';

interface HeaderProps {
  isDark: boolean;
  onToggleTheme: () => void;
  language: Language;
  onToggleLanguage: () => void;
  isConnected: boolean;
  connectedLabel: string;
  disconnectedLabel: string;
  onLogout: () => void;
}

export default function Header({
  isDark, onToggleTheme, language, onToggleLanguage,
  isConnected, connectedLabel, disconnectedLabel, onLogout,
}: HeaderProps) {
  return (
    <header className="app-header">
      <div className="header-left">
        <div className="logo-box">
          <Icon name="logo" size={16} color="var(--accent2)" />
        </div>
        <span className="logo-text">ProcureAI</span>
        <span className="beta-badge">BETA</span>
      </div>
      <div className="header-right">
        <ThemeToggle isDark={isDark} onToggle={onToggleTheme} />
        <LanguageToggle language={language} onToggle={onToggleLanguage} />
        <button className="header-btn" title="Logout" onClick={onLogout}>
          <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="var(--text2)" strokeWidth="2" strokeLinecap="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        </button>
        <div className={`connection-badge ${isConnected ? 'connected' : 'disconnected'}`}>
          <div className="pulse-dot" />
          {isConnected ? connectedLabel : disconnectedLabel}
        </div>
      </div>
    </header>
  );
}
