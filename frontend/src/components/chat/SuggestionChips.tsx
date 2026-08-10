import Icon from '../common/Icon';
import type { Suggestion } from '../../i18n/translations';

interface SuggestionChipsProps {
  suggestions: Suggestion[];
  onSelect: (label: string) => void;
}

export default function SuggestionChips({ suggestions, onSelect }: SuggestionChipsProps) {
  return (
    <div className="suggestions-strip">
      {suggestions.map((s, i) => (
        <button key={i} className="suggestion-chip" onClick={() => onSelect(s.label)}>
          <Icon name={s.icon} size={11} color="var(--accent2)" />
          {s.label}
        </button>
      ))}
    </div>
  );
}
