import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ChatPanel from '../components/chat/ChatPanel';
import { SUGGESTIONS, TRANSLATIONS } from '../i18n/translations';
import { DEMO_LIMIT_MESSAGE, useChat } from './useChat';
import { jsonResponse, mockFetch } from '../test/fetchMock';

async function sendAndGetReply(chatResponse: () => Response) {
  mockFetch({
    'GET /': () => jsonResponse({ message: 'ok' }),
    'POST /chat': chatResponse,
  });
  const { result } = renderHook(() => useChat());
  await act(() => result.current.handleSubmit('Compare bids'));
  await waitFor(() => expect(result.current.isLoading).toBe(false));
  const { messages } = result.current;
  return messages[messages.length - 1];
}

describe('useChat rate limits', () => {
  it('shows a friendly inline message when the demo quota is used up', async () => {
    const reply = await sendAndGetReply(() =>
      jsonResponse({ detail: 'Demo limit reached for today, try again tomorrow.', type: 'DemoQuotaExceededError' }, 429),
    );

    expect(reply?.sender).toBe('agent');
    expect(reply?.text).toBe(DEMO_LIMIT_MESSAGE);
    expect(reply?.text).not.toMatch(/^Error:/);
  });

  it('does not blame the demo quota for an ordinary rate limit', async () => {
    const reply = await sendAndGetReply(() => jsonResponse({ error: 'Rate limit exceeded: 10 per 1 minute' }, 429));

    expect(reply?.text).toMatch(/too many requests/i);
    expect(reply?.text).not.toBe(DEMO_LIMIT_MESSAGE);
  });
});

describe('ChatPanel upload zone', () => {
  function renderPanel(canUpload?: boolean) {
    mockFetch({ 'GET /': () => jsonResponse({ message: 'ok' }) });
    const { result } = renderHook(() => useChat());
    render(
      <ChatPanel
        chat={result.current}
        language="en"
        t={TRANSLATIONS.en}
        suggestions={SUGGESTIONS.en}
        canUpload={canUpload}
      />,
    );
  }

  it('is shown by default', () => {
    renderPanel();
    expect(screen.getByText(/click to upload/i)).toBeInTheDocument();
  });

  it('is hidden for demo accounts', () => {
    renderPanel(false);
    expect(screen.queryByText(/click to upload/i)).not.toBeInTheDocument();
  });
});
