import { useEffect, useState } from 'react';
import { SUGGESTIONS, TRANSLATIONS } from '../i18n/translations';
import type { Suggestion, Translations } from '../i18n/translations';
import type { Language } from '../types';

export interface UseI18nResult {
  language: Language;
  toggleLanguage: () => void;
  t: Translations;
  suggestions: Suggestion[];
}

export function useI18n(): UseI18nResult {
  const [language, setLanguage] = useState<Language>(() =>
    localStorage.getItem('language') === 'gr' ? 'gr' : 'en'
  );

  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  const toggleLanguage = () => setLanguage(p => (p === 'en' ? 'gr' : 'en'));

  return { language, toggleLanguage, t: TRANSLATIONS[language], suggestions: SUGGESTIONS[language] };
}
