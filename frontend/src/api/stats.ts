import { apiJson } from './client';
import type { Stats } from '../types';

export async function fetchStats(): Promise<Stats> {
  return apiJson<Stats>('/stats', {}, 'Failed to load stats');
}
