import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import MessageBubble from './MessageBubble';
import { TRANSLATIONS, toolBadge } from '../../i18n/translations';
import type { Language, Message } from '../../types';

function renderBubble(toolUsed: string, language: Language) {
  const message: Message = {
    id: 'm1',
    text: 'Answer',
    sender: 'agent',
    timestamp: new Date('2026-11-08T10:00:00Z'),
    toolUsed,
  };
  render(
    <MessageBubble message={message} language={language} viewReasoningLabel="view" hideReasoningLabel="hide" />
  );
}

describe('tool badge', () => {
  it.each([
    ['history', 'en', 'from history'],
    ['direct', 'en', 'direct answer'],
    ['history', 'gr', 'από ιστορικό'],
    ['direct', 'gr', 'απευθείας απάντηση'],
  ] as const)('labels tool-less answer %s in %s as "%s" with the neutral style', (tool, lang, label) => {
    renderBubble(tool, lang);
    const badge = screen.getByText(label);
    expect(badge).toHaveClass('tool-badge', 'neutral');
    expect(badge).toHaveTextContent(new RegExp(`^${label}$`));
  });

  it('keeps real tool names with the gear and the default style', () => {
    renderBubble('supplier_lookup', 'gr');
    const badge = screen.getByText('⚙ supplier_lookup');
    expect(badge).toHaveClass('tool-badge');
    expect(badge).not.toHaveClass('neutral');
  });

  it('gives the Results panel the same localized, neutral labels', () => {
    expect(toolBadge('history', TRANSLATIONS.en)).toEqual({ label: 'from history', neutral: true });
    expect(toolBadge('direct', TRANSLATIONS.gr)).toEqual({ label: 'απευθείας απάντηση', neutral: true });
    expect(toolBadge('bid_comparison', TRANSLATIONS.en)).toEqual({ label: 'bid_comparison', neutral: false });
  });
});
