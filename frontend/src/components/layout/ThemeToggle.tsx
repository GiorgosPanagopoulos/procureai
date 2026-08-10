import Icon from '../common/Icon';

interface ThemeToggleProps {
  isDark: boolean;
  onToggle: () => void;
}

export default function ThemeToggle({ isDark, onToggle }: ThemeToggleProps) {
  return (
    <button
      className="header-btn"
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      onClick={onToggle}
    >
      {isDark ? (
        <Icon name="sun" size={14} color="var(--text2)" />
      ) : (
        <svg width={14} height={14} viewBox="0 0 24 24" fill="var(--text2)">
          <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"/>
        </svg>
      )}
    </button>
  );
}
