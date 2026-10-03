import { describe, expect, it, vi } from 'vitest';
import { apiFetch, apiJson, onUnauthorized, UnauthorizedError } from './client';
import { getToken, setToken } from './token';
import { jsonResponse, mockFetch } from '../test/fetchMock';

describe('api client', () => {
  it('sends the bearer token on every request', async () => {
    setToken('tok-123');
    const fetchSpy = mockFetch({ 'GET /suppliers': () => jsonResponse([]) });

    await apiJson('/suppliers');

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer tok-123');
  });

  it('restores the token from sessionStorage', () => {
    setToken('persisted');
    expect(sessionStorage.getItem('procureai.access_token')).toBe('persisted');
    expect(getToken()).toBe('persisted');
  });

  it('on 401 clears the token, triggers the login redirect and throws', async () => {
    setToken('expired');
    const handler = vi.fn();
    const unsubscribe = onUnauthorized(handler);
    mockFetch({ 'GET /stats': () => jsonResponse({ detail: 'Invalid or expired token' }, 401) });

    await expect(apiJson('/stats')).rejects.toBeInstanceOf(UnauthorizedError);

    expect(handler).toHaveBeenCalledOnce();
    expect(getToken()).toBeNull();
    expect(sessionStorage.getItem('procureai.access_token')).toBeNull();
    unsubscribe();
  });

  it('does not redirect when the caller expects a 401', async () => {
    setToken('tok');
    const handler = vi.fn();
    const unsubscribe = onUnauthorized(handler);
    mockFetch({ 'POST /auth/login': () => jsonResponse({ detail: 'Incorrect email or password' }, 401) });

    const res = await apiFetch('/auth/login', { method: 'POST', skipAuthRedirect: true });

    expect(res.status).toBe(401);
    expect(handler).not.toHaveBeenCalled();
    unsubscribe();
  });

  it('surfaces server errors instead of returning empty data', async () => {
    mockFetch({ 'GET /bids': () => jsonResponse({ detail: 'boom' }, 500) });
    await expect(apiJson('/bids')).rejects.toThrow('boom');
  });
});
