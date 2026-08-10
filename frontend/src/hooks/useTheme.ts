import { useEffect, useState } from 'react';

export interface UseThemeResult {
  isDark: boolean;
  toggleTheme: () => void;
}

export function useTheme(): UseThemeResult {
  const [isDark, setIsDark] = useState<boolean>(() =>
    localStorage.getItem('darkMode') !== 'false'
  );

  useEffect(() => {
    localStorage.setItem('darkMode', String(isDark));
  }, [isDark]);

  const toggleTheme = () => setIsDark(p => !p);

  return { isDark, toggleTheme };
}
