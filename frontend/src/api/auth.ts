const API_BASE = "http://localhost:8000";

export interface AuthUser {
  _id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

export async function loginApi(email: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || "Login failed");
  }
  const data = await res.json();
  return data.user;
}

export async function registerApi(email: string, password: string, full_name: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password, full_name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || "Registration failed");
  }
  return res.json();
}

export async function logoutApi(): Promise<void> {
  await fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export async function getMeApi(): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}
