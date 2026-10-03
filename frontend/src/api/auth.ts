import { ApiError, apiFetch, apiJson } from './client';
import { clearToken, getToken, setToken } from './token';
import type { AuthUser, LoginResponse, UserRole } from '../types';

export async function loginApi(email: string, password: string): Promise<AuthUser> {
  const res = await apiFetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
    skipAuthRedirect: true,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body?.detail || 'Login failed');
  const data = body as LoginResponse;
  if (!data?.access_token) throw new ApiError(res.status, 'Login response did not include a token');
  setToken(data.access_token);
  return data.user;
}

// Admin-only on the backend; not exposed in the UI.
export async function registerApi(
  email: string,
  password: string,
  full_name: string,
  role: UserRole = 'viewer',
): Promise<AuthUser> {
  try {
    return await apiJson<AuthUser>('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name, role }),
    }, 'Registration failed');
  } catch (err) {
    if (err instanceof ApiError && err.status === 403) {
      throw new ApiError(403, 'Only administrators can create accounts.');
    }
    throw err;
  }
}

export async function logoutApi(): Promise<void> {
  try {
    await apiFetch('/auth/logout', { method: 'POST', skipAuthRedirect: true });
  } finally {
    clearToken();
  }
}

export async function getMeApi(): Promise<AuthUser> {
  if (!getToken()) throw new ApiError(401, 'Not authenticated');
  try {
    return await apiJson<AuthUser>('/auth/me', { skipAuthRedirect: true }, 'Not authenticated');
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) clearToken();
    throw err;
  }
}
