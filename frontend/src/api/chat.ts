import type { AgentResponse, Bid, Supplier } from '../types';

const API_BASE = 'http://localhost:8000';

export async function fetchWithTimeout(input: RequestInfo, init?: RequestInit, timeout = 15000): Promise<Response> {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), timeout);
  try {
    return await fetch(input, { ...init, signal: ctrl.signal, credentials: 'include' as RequestCredentials });
  } finally {
    clearTimeout(id);
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function sendChatMessage(message: string, conversationId: string | null): Promise<AgentResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  }, 60000);

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || res.statusText || 'Request failed');
  }
  return res.json();
}

export async function uploadDocument(file: File): Promise<{ message?: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetchWithTimeout(`${API_BASE}/upload`, { method: 'POST', body: formData }, 20000);
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || 'Upload failed');
  }
  return res.json();
}

export async function fetchSuppliers(): Promise<Supplier[]> {
  const res = await fetchWithTimeout(`${API_BASE}/suppliers`, undefined, 15000);
  if (!res.ok) throw new Error('Failed to fetch suppliers');
  return res.json();
}

export async function fetchBids(): Promise<Bid[]> {
  const res = await fetchWithTimeout(`${API_BASE}/bids`, undefined, 15000);
  if (!res.ok) throw new Error('Failed to fetch bids');
  return res.json();
}
