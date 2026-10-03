import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import HeroStats from './HeroStats';
import { jsonResponse, mockFetch } from '../../test/fetchMock';

const STATS = { suppliers: 3, bids: 4, total_value_eur: 4000, avg_delivery_days: 12.8 };

describe('HeroStats', () => {
  it('shows a skeleton, then the numbers from /stats', async () => {
    let resolve!: (r: Response) => void;
    mockFetch({ 'GET /stats': () => new Promise<Response>(r => { resolve = r; }) });

    render(<HeroStats language="en" />);
    expect(screen.getByTestId('hero-stats-loading')).toBeInTheDocument();

    resolve(jsonResponse(STATS));

    expect(await screen.findByText('3 Suppliers')).toBeInTheDocument();
    expect(screen.getByTestId('stat-suppliers')).toHaveTextContent('3 Suppliers');
    expect(screen.getByTestId('stat-bids')).toHaveTextContent('4 Bids');
    // Compact EUR output varies by ICU/CLDR version (e.g. NBSP vs no space), so allow flexible whitespace.
    expect(screen.getByTestId('stat-pipeline')).toHaveTextContent(/€\s*4K\s*Pipeline/);
    expect(screen.getByTestId('stat-delivery')).toHaveTextContent('12.8 days avg delivery');
    expect(screen.queryByTestId('hero-stats-loading')).not.toBeInTheDocument();
  });

  it('never falls back to placeholder numbers on error', async () => {
    mockFetch({ 'GET /stats': () => jsonResponse({ detail: 'Mongo down' }, 500) });

    render(<HeroStats language="en" />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Stats unavailable: Mongo down');
    expect(screen.queryByText(/128|47 Active Bids|2\.4M/)).not.toBeInTheDocument();
  });
});
