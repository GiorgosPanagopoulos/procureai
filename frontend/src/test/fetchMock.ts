import { vi } from 'vitest';

type Route = (init?: RequestInit) => Response | Promise<Response>;

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

// Routes are keyed by "METHOD /path"; unmatched requests fail the test loudly.
export function mockFetch(routes: Record<string, Route>) {
  const spy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url);
    const key = `${(init?.method ?? 'GET').toUpperCase()} ${url.pathname}`;
    const route = routes[key];
    if (!route) throw new Error(`Unexpected fetch: ${key}`);
    return route(init);
  });
  vi.stubGlobal('fetch', spy);
  return spy;
}
