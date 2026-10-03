import { render, screen } from '@testing-library/react';
import { beforeAll, describe, expect, it } from 'vitest';
import App from './App';
import { setToken } from './api/token';
import { jsonResponse, mockFetch } from './test/fetchMock';

const USER = {
  _id: 'u1',
  email: 'viewer@procureai.test',
  full_name: 'Viewer',
  is_active: true,
  is_superuser: false,
  role: 'viewer',
  created_at: '2026-01-01T00:00:00Z',
};

beforeAll(() => {
  Element.prototype.scrollIntoView ??= () => {};
});

describe('App auth flow', () => {
  it('returns to the login page when an API call answers 401', async () => {
    setToken('stale-token');
    const fetchSpy = mockFetch({
      'GET /': () => jsonResponse({ message: 'ok' }),
      'GET /auth/me': () => jsonResponse(USER),
      'GET /stats': () => jsonResponse({ detail: 'Invalid or expired token' }, 401),
    });

    render(<App />);

    expect(await screen.findByText(/session has expired/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(sessionStorage.getItem('procureai.access_token')).toBeNull();

    const meCall = fetchSpy.mock.calls.find(([url]) => String(url).endsWith('/auth/me'));
    expect(new Headers((meCall?.[1] as RequestInit).headers).get('Authorization')).toBe('Bearer stale-token');
  });

  it('has no self-registration UI', async () => {
    mockFetch({ 'GET /': () => jsonResponse({ message: 'ok' }) });

    render(<App />);

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.queryByText(/register|create account/i)).not.toBeInTheDocument();
  });
});
