import { useCallback, useEffect, useState } from 'react';
import { fetchStats } from '../api/stats';
import type { Stats } from '../types';

export type UseStatsResult =
  | { status: 'loading'; stats: null; error: null; reload: () => void }
  | { status: 'ready'; stats: Stats; error: null; reload: () => void }
  | { status: 'error'; stats: null; error: string; reload: () => void };

type StatsState =
  | { status: 'loading'; stats: null; error: null }
  | { status: 'ready'; stats: Stats; error: null }
  | { status: 'error'; stats: null; error: string };

const LOADING: StatsState = { status: 'loading', stats: null, error: null };

export function useStats(): UseStatsResult {
  const [state, setState] = useState<StatsState>(LOADING);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState(LOADING);
    fetchStats()
      .then(stats => { if (!cancelled) setState({ status: 'ready', stats, error: null }); })
      .catch(err => {
        if (!cancelled) {
          setState({ status: 'error', stats: null, error: err instanceof Error ? err.message : 'Failed to load stats' });
        }
      });
    return () => { cancelled = true; };
  }, [attempt]);

  const reload = useCallback(() => setAttempt(a => a + 1), []);
  return { ...state, reload } as UseStatsResult;
}
