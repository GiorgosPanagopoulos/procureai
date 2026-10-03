import { clearToken, getToken } from './token';

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message = 'Your session has expired. Please sign in again.') {
    super(401, message);
    this.name = 'UnauthorizedError';
  }
}

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

// The app has no router: AuthProvider registers a handler that drops the user,
// which renders the login page. Without a handler, fall back to a full reload.
export function onUnauthorized(handler: UnauthorizedHandler): () => void {
  unauthorizedHandler = handler;
  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null;
  };
}

function redirectToLogin(): void {
  clearToken();
  if (unauthorizedHandler) unauthorizedHandler();
  else window.location.assign('/');
}

export interface ApiRequestInit extends RequestInit {
  timeoutMs?: number;
  // For calls where 401 is an expected answer (e.g. wrong password on login).
  skipAuthRedirect?: boolean;
}

export async function apiFetch(path: string, init: ApiRequestInit = {}): Promise<Response> {
  const { timeoutMs = 15000, skipAuthRedirect = false, headers, ...rest } = init;
  const finalHeaders = new Headers(headers);
  const token = getToken();
  if (token) finalHeaders.set('Authorization', `Bearer ${token}`);

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: finalHeaders,
      credentials: 'include',
      signal: ctrl.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  if (res.status === 401 && !skipAuthRedirect) {
    redirectToLogin();
    throw new UnauthorizedError();
  }
  return res;
}

async function errorDetail(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => null);
  const detail = body?.detail;
  return typeof detail === 'string' && detail ? detail : res.statusText || fallback;
}

export async function apiJson<T>(path: string, init: ApiRequestInit = {}, fallbackError = 'Request failed'): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) throw new ApiError(res.status, await errorDetail(res, fallbackError));
  return res.json() as Promise<T>;
}
