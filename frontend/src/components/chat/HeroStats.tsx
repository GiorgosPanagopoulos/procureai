import { useStats } from '../../hooks/useStats';
import type { Language, Stats } from '../../types';

interface Pill {
  key: string;
  color: string;
  text: string;
}

function locale(language: Language): string {
  return language === 'gr' ? 'el-GR' : 'en-GB';
}

function buildPills(stats: Stats, language: Language): Pill[] {
  const num = new Intl.NumberFormat(locale(language));
  const eur = new Intl.NumberFormat(locale(language), {
    style: 'currency',
    currency: 'EUR',
    notation: 'compact',
    maximumFractionDigits: 1,
  });
  const pills: Pill[] = [
    { key: 'suppliers', color: 'var(--cyan)', text: `${num.format(stats.suppliers)} Suppliers` },
    { key: 'bids', color: '#a78bfa', text: `${num.format(stats.bids)} Bids` },
    { key: 'pipeline', color: 'var(--accent2)', text: `${eur.format(stats.total_value_eur)} Pipeline` },
  ];
  if (stats.avg_delivery_days !== null) {
    pills.push({
      key: 'delivery',
      color: 'var(--text2)',
      text: `${num.format(stats.avg_delivery_days)} days avg delivery`,
    });
  }
  return pills;
}

export default function HeroStats({ language }: { language: Language }) {
  const state = useStats();

  if (state.status === 'loading') {
    return (
      <div className="empty-pills" aria-busy="true" aria-label="Loading stats" data-testid="hero-stats-loading">
        {[88, 80, 96].map((w, i) => (
          <div key={i} className="empty-pill skeleton-pill" style={{ width: w }} />
        ))}
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="empty-pills" role="alert">
        <div className="empty-pill stats-error">
          Stats unavailable: {state.error}
          <button type="button" className="stats-retry" onClick={state.reload}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="empty-pills" data-testid="hero-stats">
      {buildPills(state.stats, language).map(p => (
        <div key={p.key} className="empty-pill" data-testid={`stat-${p.key}`} style={{ color: p.color }}>{p.text}</div>
      ))}
    </div>
  );
}
