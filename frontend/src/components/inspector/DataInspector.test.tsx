import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DataInspector from './DataInspector';
import { TRANSLATIONS } from '../../i18n/translations';
import type { Message } from '../../types';

const MESSAGES: Message[] = [
  { id: '1', text: 'Compare IT bids', sender: 'user', timestamp: new Date() },
  { id: '2', text: 'TechSupply has the lowest bid.', sender: 'agent', timestamp: new Date() },
];

function renderInspector(showResults?: boolean) {
  render(
    <DataInspector
      messages={MESSAGES}
      suppliers={[]}
      bids={[]}
      loadingData={null}
      onLoadSuppliers={() => {}}
      onLoadBids={() => {}}
      rightTab="results"
      onTabChange={() => {}}
      onClearChat={() => {}}
      t={TRANSLATIONS.en}
      showResults={showResults}
    />,
  );
}

describe('DataInspector results history', () => {
  it('lists past agent responses by default', () => {
    renderInspector();
    expect(screen.getByRole('button', { name: /results/i })).toBeInTheDocument();
    expect(screen.getByText('TechSupply has the lowest bid.')).toBeInTheDocument();
  });

  it('hides the tab and the responses for demo accounts, even if the results tab was selected', () => {
    renderInspector(false);
    expect(screen.queryByRole('button', { name: /results/i })).not.toBeInTheDocument();
    expect(screen.queryByText('TechSupply has the lowest bid.')).not.toBeInTheDocument();
    expect(screen.getByText(TRANSLATIONS.en.databaseRecords)).toBeInTheDocument();
  });
});
