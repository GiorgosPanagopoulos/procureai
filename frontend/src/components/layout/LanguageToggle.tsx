import Icon from '../common/Icon';
import type { Language } from '../../types';

interface LanguageToggleProps {
  language: Language;
  onToggle: () => void;
}

export default function LanguageToggle({ language, onToggle }: LanguageToggleProps) {
  return (
    <button className="header-btn lang" onClick={onToggle} title="Switch language">
      <Icon name="globe" size={13} color="var(--text2)" />
      {language.toUpperCase()}
    </button>
  );
}
